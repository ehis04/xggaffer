from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from apps.playerdata.models import ClubSeasonEnrichment, PlayerSeasonEnrichment
from apps.players.models import ExternalProvider
from apps.clubs.models import ClubImportJob, ClubMembership,ClubPlayer, ClubResource

from django.db import transaction
from django.utils import timezone

try:
    from openpyxl import load_workbook
except ImportError:  # pragma: no cover
    load_workbook = None


class ClubImportValidationError(Exception):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}

class ClubImportCommitError(Exception):
    pass

@dataclass(frozen=True)
class FieldSpec:
    coercer: Callable[[Any], Any]
    required: bool = False
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImportSchema:
    fields: dict[str, FieldSpec]
    required_header_groups: tuple[tuple[str, ...], ...] = ()
    required_value_groups: tuple[tuple[str, ...], ...] = ()
    target_model: str = ''


@dataclass
class ImportRowResult:
    row_number: int
    raw_data: dict[str, Any]
    normalised_data: dict[str, Any]
    status: str
    match_method: str | None = None
    target_model: str | None = None
    target_id: int | None = None
    target_label: str | None = None
    proposed_record_key: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            'row_number': self.row_number,
            'raw_data': _serialise_preview_value(self.raw_data),
            'normalised_data': _serialise_preview_value(self.normalised_data),
            'status': self.status,
            'match_method': self.match_method,
            'target_model': self.target_model,
            'target_id': self.target_id,
            'target_label': self.target_label,
            'proposed_record_key': self.proposed_record_key,
            'warnings': self.warnings,
            'errors': self.errors,
        }


@dataclass
class ImportValidationResult:
    job_id: int
    import_type: str
    source_resource_id: int
    headers: list[str]
    normalised_headers: list[str]
    rows: list[ImportRowResult]
    is_raw_preview: bool = False

    @property
    def total_rows(self) -> int:
        return len(self.rows)

    @property
    def valid_row_count(self) -> int:
        return sum(1 for row in self.rows if row.status == 'matched')

    @property
    def skipped_row_count(self) -> int:
        return sum(1 for row in self.rows if row.status == 'skipped')

    @property
    def unmatched_row_count(self) -> int:
        return sum(1 for row in self.rows if row.status == 'unmatched')

    @property
    def ambiguous_row_count(self) -> int:
        return sum(1 for row in self.rows if row.status == 'ambiguous')

    @property
    def invalid_row_count(self) -> int:
        return sum(1 for row in self.rows if row.status == 'invalid')

    @property
    def warning_count(self) -> int:
        return sum(len(row.warnings) for row in self.rows)

    def to_preview_payload(self) -> dict[str, Any]:
        payload = {
            'job_id': self.job_id,
            'import_type': self.import_type,
            'source_resource_id': self.source_resource_id,
            'headers': self.headers,
            'normalised_headers': self.normalised_headers,
            'counts': {
                'total_rows': self.total_rows,
                'valid_rows': self.valid_row_count,
                'skipped_rows': self.skipped_row_count,
                'unmatched_rows': self.unmatched_row_count,
                'ambiguous_rows': self.ambiguous_row_count,
                'invalid_rows': self.invalid_row_count,
                'warning_count': self.warning_count,
            },
            'rows': [row.to_dict() for row in self.rows],
        }

        if self.is_raw_preview:
            payload['raw_preview'] = True

        return payload


CLUB_PLAYER_POSITION_VALUES = {
    value for value, _label in ClubPlayer._meta.get_field('primary_position').choices
}
CLUB_PLAYER_FOOT_VALUES = {
    value for value, _label in ClubPlayer._meta.get_field('preferred_foot').choices
}
PROVIDER_VALUES = {
    value for value, _label in ExternalProvider.choices
}

PLAYER_PROFILE_UPDATE_FIELDS = (
    'first_name',
    'last_name',
    'display_name',
    'squad_number',
    'primary_position',
    'secondary_position',
    'preferred_foot',
    'date_of_birth',
    'height_cm',
    'is_active',
    'is_public',
)

PLAYER_PROFILE_IDENTIFIER_FIELDS = (
    'club_player_id',
    'squad_number',
    'full_name',
    'display_name',
)

PLAYER_SEASON_IDENTIFIER_FIELDS = (
    'club_player_id',
    'canonical_player_id',
    'squad_number',
    'full_name',
    'display_name',
)

PLAYER_SEASON_STAT_FIELDS = (
    'matches_played',
    'minutes_played',
    'goals',
    'assists',
    'shots',
    'xg',
    'xa',
    'npg',
    'npxg',
    'xg_chain',
    'xg_buildup',
    'yellow_cards',
    'red_cards',
    'key_passes',
)

SQUAD_METRIC_FIELDS = (
    'matches_played',
    'wins',
    'draws',
    'losses',
    'goals_for',
    'goals_against',
    'xg',
    'xga',
    'npxg',
    'ppda',
)

LINKED_CLUB_PLAYER_WARNING_FIELDS = {
    'first_name',
    'last_name',
    'display_name',
    'primary_position',
    'secondary_position',
    'preferred_foot',
    'date_of_birth',
    'height_cm',
}

def validate_import_job(job: ClubImportJob) -> ImportValidationResult:
    _validate_job_source(job)

    if job.import_type == ClubImportJob.ImportType.OTHER:
        return _build_raw_preview_fallback(job)

    if job.import_type not in IMPORT_SCHEMAS:
        raise ClubImportValidationError(
            f'Unsupported import_type: {job.import_type}'
        )

    try:
        return _validate_structured_import_job(job)
    except ClubImportValidationError as exc:
        if (
            job.import_type == ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE
            and exc.details
            and any(
                key in exc.details
                for key in (
                    'missing_required_headers',
                    'missing_header_groups',
                    'duplicate_headers',
                )
            )
        ):
            return _build_raw_preview_fallback(job)
        raise


def _build_raw_preview_fallback(job: ClubImportJob) -> ImportValidationResult:
    headers, raw_rows = _read_tabular_resource(job.source_resource)

    rows: list[ImportRowResult] = []
    for row_number, raw_row in enumerate(raw_rows, start=2):
        if _row_is_blank(raw_row):
            rows.append(
                ImportRowResult(
                    row_number=row_number,
                    raw_data=raw_row,
                    normalised_data={},
                    status='skipped',
                )
            )
        else:
            rows.append(
                ImportRowResult(
                    row_number=row_number,
                    raw_data=raw_row,
                    normalised_data={},
                    status='preview',
                )
            )

    return ImportValidationResult(
        job_id=job.id,
        import_type=job.import_type,
        source_resource_id=job.source_resource_id,
        headers=headers,
        normalised_headers=headers,
        rows=rows,
        is_raw_preview=True,
    )


def _validate_structured_import_job(job: ClubImportJob) -> ImportValidationResult:
    schema = IMPORT_SCHEMAS[job.import_type]
    headers, raw_rows = _read_tabular_resource(job.source_resource)
    header_mapping, normalised_headers = _canonicalise_headers(headers, schema)
    _validate_header_contract(normalised_headers, schema)

    club_players = list(
        ClubPlayer.objects.filter(club=job.club).select_related('player')
    )

    rows: list[ImportRowResult] = []
    seen_squad_metric_keys: set[tuple[str, str]] = set()

    for row_number, raw_row in enumerate(raw_rows, start=2):
        if _row_is_blank(raw_row):
            rows.append(
                ImportRowResult(
                    row_number=row_number,
                    raw_data=raw_row,
                    normalised_data={},
                    status='skipped',
                    target_model=schema.target_model,
                )
            )
            continue

        canonical_row = {
            header_mapping[header]: value
            for header, value in raw_row.items()
            if header in header_mapping
        }

        normalised_data, row_errors = _coerce_row(canonical_row, schema)

        for group in schema.required_value_groups:
            if not any(normalised_data.get(field_name) is not None for field_name in group):
                row_errors.append(
                    f'At least one of {", ".join(group)} must contain a value.'
                )

        if row_errors:
            rows.append(
                ImportRowResult(
                    row_number=row_number,
                    raw_data=raw_row,
                    normalised_data=normalised_data,
                    status='invalid',
                    target_model=schema.target_model,
                    errors=row_errors,
                )
            )
            continue

        if job.import_type == ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE:
            rows.append(
                _resolve_player_profile_row(
                    row_number=row_number,
                    raw_row=raw_row,
                    normalised_data=normalised_data,
                    club_players=club_players,
                )
            )
            continue

        if job.import_type == ClubImportJob.ImportType.PLAYER_SEASON_STATS:
            rows.append(
                _resolve_player_season_row(
                    row_number=row_number,
                    raw_row=raw_row,
                    normalised_data=normalised_data,
                    club_players=club_players,
                )
            )
            continue

        rows.append(
            _resolve_squad_metrics_row(
                row_number=row_number,
                raw_row=raw_row,
                normalised_data=normalised_data,
                club_id=job.club_id,
                seen_keys=seen_squad_metric_keys,
            )
        )

    return ImportValidationResult(
        job_id=job.id,
        import_type=job.import_type,
        source_resource_id=job.source_resource_id,
        headers=headers,
        normalised_headers=normalised_headers,
        rows=rows,
    )


def _validate_job_source(job: ClubImportJob) -> None:
    if job.source_resource_id is None:
        raise ClubImportValidationError('ClubImportJob must have a source_resource before validation.')

    if job.source_resource.club_id != job.club_id:
        raise ClubImportValidationError(
            'source_resource must belong to the same club as the import job.'
        )

    if job.source_resource.file_kind not in {
        ClubResource.FileKind.CSV,
        ClubResource.FileKind.XLSX,
    }:
        raise ClubImportValidationError(
            'source_resource must be a CSV or XLSX ClubResource.'
        )

    if not job.source_resource.file:
        raise ClubImportValidationError(
            'source_resource does not have an attached file to parse.'
        )


def _read_tabular_resource(resource: ClubResource) -> tuple[list[str], list[dict[str, Any]]]:
    if resource.file_kind == ClubResource.FileKind.CSV:
        return _read_csv_rows(resource)

    if resource.file_kind == ClubResource.FileKind.XLSX:
        return _read_xlsx_rows(resource)

    raise ClubImportValidationError(
        f'Unsupported file_kind for import parsing: {resource.file_kind}'
    )


def _read_csv_rows(resource: ClubResource) -> tuple[list[str], list[dict[str, Any]]]:
    resource.file.open('rb')
    try:
        text_stream = io.TextIOWrapper(resource.file, encoding='utf-8-sig', newline='')
        reader = csv.DictReader(text_stream)
        headers = list(reader.fieldnames or [])

        if not headers:
            raise ClubImportValidationError('CSV file must include a header row.')

        rows = [dict(row) for row in reader]
        return headers, rows
    finally:
        try:
            text_stream.detach()
        except Exception:
            pass
        resource.file.close()


def _read_xlsx_rows(resource: ClubResource) -> tuple[list[str], list[dict[str, Any]]]:
    if load_workbook is None:
        raise ClubImportValidationError(
            'XLSX parsing requires openpyxl to be installed.'
        )

    resource.file.open('rb')
    try:
        workbook = load_workbook(resource.file, read_only=True, data_only=True)
        worksheet = workbook.active
        iterator = worksheet.iter_rows(values_only=True)

        header_row = next(iterator, None)
        if header_row is None:
            raise ClubImportValidationError('XLSX file must include a header row.')

        headers = [str(value).strip() if value is not None else '' for value in header_row]
        if not any(headers):
            raise ClubImportValidationError('XLSX header row cannot be blank.')

        rows: list[dict[str, Any]] = []
        for values in iterator:
            row = {
                headers[index]: values[index] if index < len(values) else None
                for index in range(len(headers))
            }
            rows.append(row)

        return headers, rows
    finally:
        try:
            workbook.close()
        except Exception:
            pass
        resource.file.close()


def _canonicalise_headers(
    headers: list[str],
    schema: ImportSchema,
) -> tuple[dict[str, str], list[str]]:
    alias_map: dict[str, str] = {}

    for field_name, spec in schema.fields.items():
        alias_map[_normalise_header(field_name)] = field_name
        for alias in spec.aliases:
            alias_map[_normalise_header(alias)] = field_name

    mapping: dict[str, str] = {}
    seen_canonical: set[str] = set()
    duplicate_headers: list[str] = []

    for header in headers:
        normalised_header = _normalise_header(header)
        canonical_name = alias_map.get(normalised_header)

        if not canonical_name:
            # Unknown columns are silently skipped — they won't be processed.
            continue

        if canonical_name in seen_canonical:
            duplicate_headers.append(canonical_name)
            continue

        mapping[header] = canonical_name
        seen_canonical.add(canonical_name)

    if duplicate_headers:
        raise ClubImportValidationError(
            'File headers do not match the supported schema for this import type.',
            details={'duplicate_headers': duplicate_headers},
        )

    return mapping, list(seen_canonical)


def _validate_header_contract(
    normalised_headers: list[str],
    schema: ImportSchema,
) -> None:
    missing_required_headers = [
        field_name
        for field_name, spec in schema.fields.items()
        if spec.required and field_name not in normalised_headers
    ]

    missing_groups: list[list[str]] = []
    for group in schema.required_header_groups:
        if not any(field_name in normalised_headers for field_name in group):
            missing_groups.append(list(group))

    if missing_required_headers or missing_groups:
        raise ClubImportValidationError(
            'File headers do not satisfy the required schema for this import type.',
            details={
                'missing_required_headers': missing_required_headers,
                'missing_header_groups': missing_groups,
            },
        )


def _coerce_row(
    row: dict[str, Any],
    schema: ImportSchema,
) -> tuple[dict[str, Any], list[str]]:
    normalised_data: dict[str, Any] = {}
    row_errors: list[str] = []

    for field_name, spec in schema.fields.items():
        if field_name not in row:
            continue

        raw_value = row.get(field_name)

        if _is_blank(raw_value):
            if spec.required:
                row_errors.append(f'{field_name} is required.')
            continue

        try:
            normalised_data[field_name] = spec.coercer(raw_value)
        except ValueError as exc:
            row_errors.append(f'{field_name}: {exc}')

    return normalised_data, row_errors


def _resolve_player_profile_row(
    *,
    row_number: int,
    raw_row: dict[str, Any],
    normalised_data: dict[str, Any],
    club_players: list[ClubPlayer],
) -> ImportRowResult:
    match = _match_club_player(normalised_data, club_players)

    if match['status'] != 'matched':
        return ImportRowResult(
            row_number=row_number,
            raw_data=raw_row,
            normalised_data=normalised_data,
            status=match['status'],
            match_method=match.get('match_method'),
            target_model='ClubPlayer',
            warnings=match.get('warnings', []),
            errors=match.get('errors', []),
        )

    club_player: ClubPlayer = match['club_player']
    warnings = list(match.get('warnings', []))

    if club_player.player_id and any(
        field_name in normalised_data for field_name in LINKED_CLUB_PLAYER_WARNING_FIELDS
    ):
        warnings.append(
            'This club player is linked to a canonical Player. Local identity changes may not '
            'alter the displayed identity in all club/player views.'
        )

    return ImportRowResult(
        row_number=row_number,
        raw_data=raw_row,
        normalised_data=normalised_data,
        status='matched',
        match_method=match['match_method'],
        target_model='ClubPlayer',
        target_id=club_player.id,
        target_label=club_player.full_name,
        proposed_record_key=f'club_player:{club_player.id}',
        warnings=warnings,
    )


def _resolve_player_season_row(
    *,
    row_number: int,
    raw_row: dict[str, Any],
    normalised_data: dict[str, Any],
    club_players: list[ClubPlayer],
) -> ImportRowResult:
    if (
        normalised_data.get('canonical_player_id') is not None and
        normalised_data.get('club_player_id') is not None
    ):
        explicit_club_player = next(
            (player for player in club_players if player.id == normalised_data['club_player_id']),
            None,
        )
        if explicit_club_player is None:
            return ImportRowResult(
                row_number=row_number,
                raw_data=raw_row,
                normalised_data=normalised_data,
                status='unmatched',
                match_method='explicit_id',
                target_model='PlayerSeasonEnrichment',
                errors=['club_player_id does not match a ClubPlayer in this club.'],
            )
        if explicit_club_player.player_id != normalised_data['canonical_player_id']:
            return ImportRowResult(
                row_number=row_number,
                raw_data=raw_row,
                normalised_data=normalised_data,
                status='invalid',
                target_model='PlayerSeasonEnrichment',
                errors=[
                    'club_player_id and canonical_player_id refer to different canonical players.'
                ],
            )

    match = _match_player_enrichment_target(normalised_data, club_players)

    if match['status'] != 'matched':
        return ImportRowResult(
            row_number=row_number,
            raw_data=raw_row,
            normalised_data=normalised_data,
            status=match['status'],
            match_method=match.get('match_method'),
            target_model='PlayerSeasonEnrichment',
            warnings=match.get('warnings', []),
            errors=match.get('errors', []),
        )

    club_player: ClubPlayer = match['club_player']
    player = club_player.player

    competition_code = normalised_data.get('competition_code') or ''
    external_team_id = normalised_data.get('external_team_id') or ''
    proposed_key = (
        f'player_season_enrichment:{player.id}:'
        f'{normalised_data["provider"]}:'
        f'{normalised_data["season_label"]}:'
        f'{competition_code}:'
        f'{external_team_id}'
    )

    return ImportRowResult(
        row_number=row_number,
        raw_data=raw_row,
        normalised_data=normalised_data,
        status='matched',
        match_method=match['match_method'],
        target_model='PlayerSeasonEnrichment',
        target_id=player.id,
        target_label=player.display_name or player.full_name,
        proposed_record_key=proposed_key,
        warnings=match.get('warnings', []),
    )


def _resolve_squad_metrics_row(
    *,
    row_number: int,
    raw_row: dict[str, Any],
    normalised_data: dict[str, Any],
    club_id: int,
    seen_keys: set[tuple[str, str]],
) -> ImportRowResult:
    key = (
        normalised_data['season_label'],
        normalised_data.get('competition_code') or '',
    )

    if key in seen_keys:
        return ImportRowResult(
            row_number=row_number,
            raw_data=raw_row,
            normalised_data=normalised_data,
            status='invalid',
            target_model='ClubSeasonEnrichment',
            errors=[
                'Duplicate season_label and competition_code combination in the same import file.'
            ],
        )

    seen_keys.add(key)

    proposed_key = (
        f'club_season_enrichment:{club_id}:'
        f'{normalised_data["provider"]}:'
        f'{normalised_data["season_label"]}:'
        f'{normalised_data.get("competition_code") or ""}'
    )

    return ImportRowResult(
        row_number=row_number,
        raw_data=raw_row,
        normalised_data=normalised_data,
        status='matched',
        match_method='club_context',
        target_model='ClubSeasonEnrichment',
        target_id=club_id,
        target_label=f'Club {club_id}',
        proposed_record_key=proposed_key,
    )


def _match_club_player(
    normalised_data: dict[str, Any],
    club_players: list[ClubPlayer],
) -> dict[str, Any]:
    warnings: list[str] = []

    club_player_id = normalised_data.get('club_player_id')
    squad_number = normalised_data.get('squad_number')
    lookup_name = _normalise_lookup_name(
        normalised_data.get('full_name') or normalised_data.get('display_name')
    )

    if club_player_id is not None:
        matches = [player for player in club_players if player.id == club_player_id]
        if not matches:
            return {
                'status': 'unmatched',
                'match_method': 'explicit_id',
                'errors': ['club_player_id does not match a ClubPlayer in this club.'],
            }

        matched = matches[0]
        _append_identifier_mismatch_warnings(
            warnings=warnings,
            matched_player=matched,
            squad_number=squad_number,
            lookup_name=lookup_name,
        )
        return {
            'status': 'matched',
            'match_method': 'explicit_id',
            'club_player': matched,
            'warnings': warnings,
        }

    if squad_number is not None:
        matches = [
            player for player in club_players
            if player.squad_number == squad_number
        ]
        if not matches:
            return {
                'status': 'unmatched',
                'match_method': 'squad_number',
                'errors': ['squad_number does not match a ClubPlayer in this club.'],
            }

        matched = matches[0]
        _append_identifier_mismatch_warnings(
            warnings=warnings,
            matched_player=matched,
            squad_number=squad_number,
            lookup_name=lookup_name,
        )
        return {
            'status': 'matched',
            'match_method': 'squad_number',
            'club_player': matched,
            'warnings': warnings,
        }

    if lookup_name:
        matches = [
            player for player in club_players
            if lookup_name in _club_player_name_candidates(player)
        ]

        if len(matches) == 1:
            return {
                'status': 'matched',
                'match_method': 'exact_name',
                'club_player': matches[0],
                'warnings': warnings,
            }

        if len(matches) > 1:
            return {
                'status': 'ambiguous',
                'match_method': 'exact_name',
                'errors': ['Exact name matched more than one ClubPlayer in this club.'],
            }

        return {
            'status': 'unmatched',
            'match_method': 'exact_name',
            'errors': ['Exact name did not match any ClubPlayer in this club.'],
        }

    return {
        'status': 'invalid',
        'errors': ['No recognised identifier was supplied for ClubPlayer matching.'],
    }


def _match_player_enrichment_target(
    normalised_data: dict[str, Any],
    club_players: list[ClubPlayer],
) -> dict[str, Any]:
    warnings: list[str] = []
    club_player_id = normalised_data.get('club_player_id')
    canonical_player_id = normalised_data.get('canonical_player_id')
    squad_number = normalised_data.get('squad_number')
    lookup_name = _normalise_lookup_name(
        normalised_data.get('full_name') or normalised_data.get('display_name')
    )

    if club_player_id is not None:
        matches = [player for player in club_players if player.id == club_player_id]
        if not matches:
            return {
                'status': 'unmatched',
                'match_method': 'explicit_id',
                'errors': ['club_player_id does not match a ClubPlayer in this club.'],
            }

        club_player = matches[0]
        if club_player.player_id is None:
            return {
                'status': 'unmatched',
                'match_method': 'explicit_id',
                'errors': [
                    'Matched ClubPlayer is not linked to a canonical Player, so '
                    'PlayerSeasonEnrichment cannot be targeted safely.'
                ],
            }

        if canonical_player_id is not None and canonical_player_id != club_player.player_id:
            warnings.append(
                'canonical_player_id did not match the ClubPlayer linked canonical Player. '
                'club_player_id was used because it is the club-scoped explicit identifier.'
            )

        _append_identifier_mismatch_warnings(
            warnings=warnings,
            matched_player=club_player,
            squad_number=squad_number,
            lookup_name=lookup_name,
        )

        return {
            'status': 'matched',
            'match_method': 'explicit_id',
            'club_player': club_player,
            'warnings': warnings,
        }

    if canonical_player_id is not None:
        matches = [
            player for player in club_players
            if player.player_id == canonical_player_id
        ]

        if not matches:
            return {
                'status': 'unmatched',
                'match_method': 'explicit_id',
                'errors': [
                    'canonical_player_id does not resolve to a canonical Player linked through '
                    'a ClubPlayer in this club.'
                ],
            }

        if len(matches) > 1:
            return {
                'status': 'ambiguous',
                'match_method': 'explicit_id',
                'errors': [
                    'canonical_player_id matched more than one ClubPlayer in this club.'
                ],
            }

        matched = matches[0]
        _append_identifier_mismatch_warnings(
            warnings=warnings,
            matched_player=matched,
            squad_number=squad_number,
            lookup_name=lookup_name,
        )
        return {
            'status': 'matched',
            'match_method': 'explicit_id',
            'club_player': matched,
            'warnings': warnings,
        }

    if squad_number is not None:
        matches = [
            player for player in club_players
            if player.squad_number == squad_number
        ]

        if not matches:
            return {
                'status': 'unmatched',
                'match_method': 'squad_number',
                'errors': ['squad_number does not match a ClubPlayer in this club.'],
            }

        matched = matches[0]
        if matched.player_id is None:
            return {
                'status': 'unmatched',
                'match_method': 'squad_number',
                'errors': [
                    'Matched ClubPlayer is not linked to a canonical Player, so '
                    'PlayerSeasonEnrichment cannot be targeted safely.'
                ],
            }

        _append_identifier_mismatch_warnings(
            warnings=warnings,
            matched_player=matched,
            squad_number=squad_number,
            lookup_name=lookup_name,
        )
        return {
            'status': 'matched',
            'match_method': 'squad_number',
            'club_player': matched,
            'warnings': warnings,
        }

    if lookup_name:
        matches = [
            player for player in club_players
            if lookup_name in _club_player_name_candidates(player)
        ]

        if len(matches) == 1:
            matched = matches[0]
            if matched.player_id is None:
                return {
                    'status': 'unmatched',
                    'match_method': 'exact_name',
                    'errors': [
                        'Matched ClubPlayer is not linked to a canonical Player, so '
                        'PlayerSeasonEnrichment cannot be targeted safely.'
                    ],
                }

            return {
                'status': 'matched',
                'match_method': 'exact_name',
                'club_player': matched,
                'warnings': warnings,
            }

        if len(matches) > 1:
            return {
                'status': 'ambiguous',
                'match_method': 'exact_name',
                'errors': ['Exact name matched more than one ClubPlayer in this club.'],
            }

        return {
            'status': 'unmatched',
            'match_method': 'exact_name',
            'errors': ['Exact name did not match any ClubPlayer in this club.'],
        }

    return {
        'status': 'invalid',
        'errors': ['No recognised identifier was supplied for player season matching.'],
    }


def _append_identifier_mismatch_warnings(
    *,
    warnings: list[str],
    matched_player: ClubPlayer,
    squad_number: int | None,
    lookup_name: str | None,
) -> None:
    if squad_number is not None and matched_player.squad_number != squad_number:
        warnings.append(
            'squad_number did not match the resolved target, but a higher-priority explicit identifier was used.'
        )

    if lookup_name and lookup_name not in _club_player_name_candidates(matched_player):
        warnings.append(
            'Exact name did not match the resolved target, but a higher-priority identifier was used.'
        )


def _club_player_name_candidates(club_player: ClubPlayer) -> set[str]:
    candidates: set[str] = set()

    local_full_name = f'{club_player.first_name} {club_player.last_name}'.strip()
    if local_full_name:
        candidates.add(_normalise_lookup_name(local_full_name))

    if club_player.display_name:
        candidates.add(_normalise_lookup_name(club_player.display_name))

    if club_player.player_id:
        canonical_full_name = club_player.player.full_name.strip()
        if canonical_full_name:
            candidates.add(_normalise_lookup_name(canonical_full_name))

        if club_player.player.display_name:
            candidates.add(_normalise_lookup_name(club_player.player.display_name))

    return {candidate for candidate in candidates if candidate}


def _normalise_lookup_name(value: str | None) -> str | None:
    if not value:
        return None
    collapsed = re.sub(r'\s+', ' ', value).strip().casefold()
    return collapsed or None


def _row_is_blank(row: dict[str, Any]) -> bool:
    return all(_is_blank(value) for value in row.values())


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ''
    return False


def _normalise_header(value: Any) -> str:
    return re.sub(r'[^a-z0-9]+', '_', str(value).strip().lower()).strip('_')


def _coerce_string(value: Any) -> str:
    return str(value).strip()


def _coerce_non_empty_string(value: Any) -> str:
    result = _coerce_string(value)
    if not result:
        raise ValueError('must not be blank.')
    return result


def _coerce_upper_string(value: Any) -> str:
    result = _coerce_string(value)
    return result.upper()


def _coerce_positive_int(value: Any) -> int:
    result = _coerce_int(value)
    if result <= 0:
        raise ValueError('must be greater than 0.')
    return result


def _coerce_non_negative_int(value: Any) -> int:
    result = _coerce_int(value)
    if result < 0:
        raise ValueError('must be 0 or greater.')
    return result


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError('must be an integer, not a boolean.')

    if isinstance(value, int):
        return value

    if isinstance(value, Decimal):
        if value != value.to_integral_value():
            raise ValueError('must be a whole number.')
        return int(value)

    value_as_string = str(value).strip()
    if not value_as_string:
        raise ValueError('must not be blank.')

    try:
        decimal_value = Decimal(value_as_string)
    except InvalidOperation as exc:
        raise ValueError('must be a valid integer.') from exc

    if decimal_value != decimal_value.to_integral_value():
        raise ValueError('must be a whole number.')

    return int(decimal_value)


def _coerce_non_negative_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        result = Decimal(str(value))
    else:
        value_as_string = str(value).strip()
        if not value_as_string:
            raise ValueError('must not be blank.')
        try:
            result = Decimal(value_as_string)
        except InvalidOperation as exc:
            raise ValueError('must be a valid decimal number.') from exc

    if result < 0:
        raise ValueError('must be 0 or greater.')

    return result


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    value_as_string = str(value).strip().casefold()
    truthy = {'true', '1', 'yes', 'y'}
    falsy = {'false', '0', 'no', 'n'}

    if value_as_string in truthy:
        return True
    if value_as_string in falsy:
        return False

    raise ValueError('must be a boolean value such as true/false, yes/no, or 1/0.')


def _coerce_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value_as_string = str(value).strip()
    if not value_as_string:
        raise ValueError('must not be blank.')

    try:
        return datetime.strptime(value_as_string, '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError('must use ISO format YYYY-MM-DD.') from exc


def _coerce_position_code(value: Any) -> str:
    result = _coerce_upper_string(value)
    if result not in CLUB_PLAYER_POSITION_VALUES:
        raise ValueError(
            f'must be one of: {", ".join(sorted(CLUB_PLAYER_POSITION_VALUES))}.'
        )
    return result


def _coerce_preferred_foot_code(value: Any) -> str:
    result = _coerce_upper_string(value)
    if result not in CLUB_PLAYER_FOOT_VALUES:
        raise ValueError(
            f'must be one of: {", ".join(sorted(CLUB_PLAYER_FOOT_VALUES))}.'
        )
    return result


def _coerce_provider(value: Any) -> str:
    result = _coerce_string(value)
    if result not in PROVIDER_VALUES:
        raise ValueError(
            f'must be one of: {", ".join(sorted(PROVIDER_VALUES))}.'
        )
    return result


def _serialise_preview_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _serialise_preview_value(nested_value)
            for key, nested_value in value.items()
        }

    if isinstance(value, list):
        return [_serialise_preview_value(item) for item in value]

    return value


PLAYER_PROFILE_SCHEMA = ImportSchema(
    target_model='ClubPlayer',
    fields={
        'club_player_id': FieldSpec(_coerce_positive_int, aliases=('id',)),
        'full_name': FieldSpec(_coerce_non_empty_string, aliases=('name', 'player_name')),
        'first_name': FieldSpec(_coerce_non_empty_string),
        'last_name': FieldSpec(_coerce_non_empty_string),
        'display_name': FieldSpec(_coerce_string),
        'squad_number': FieldSpec(_coerce_positive_int),
        'primary_position': FieldSpec(_coerce_position_code),
        'secondary_position': FieldSpec(_coerce_position_code),
        'preferred_foot': FieldSpec(_coerce_preferred_foot_code),
        'date_of_birth': FieldSpec(_coerce_date),
        'height_cm': FieldSpec(_coerce_positive_int),
        'is_active': FieldSpec(_coerce_bool),
        'is_public': FieldSpec(_coerce_bool),
    },
    required_header_groups=(
        PLAYER_PROFILE_IDENTIFIER_FIELDS,
        PLAYER_PROFILE_UPDATE_FIELDS,
    ),
    required_value_groups=(
        PLAYER_PROFILE_IDENTIFIER_FIELDS,
        PLAYER_PROFILE_UPDATE_FIELDS,
    ),
)

PLAYER_SEASON_SCHEMA = ImportSchema(
    target_model='PlayerSeasonEnrichment',
    fields={
        'provider': FieldSpec(_coerce_provider, required=True),
        'season_label': FieldSpec(_coerce_non_empty_string, required=True, aliases=('season',)),
        'competition_code': FieldSpec(_coerce_upper_string),
        'competition_name': FieldSpec(_coerce_string),
        'external_player_id': FieldSpec(_coerce_string),
        'external_team_id': FieldSpec(_coerce_string),
        'canonical_player_id': FieldSpec(_coerce_positive_int, aliases=('player_id',)),
        'club_player_id': FieldSpec(_coerce_positive_int),
        'full_name': FieldSpec(_coerce_non_empty_string, aliases=('name', 'player_name')),
        'display_name': FieldSpec(_coerce_string),
        'squad_number': FieldSpec(_coerce_positive_int),
        'matches_played': FieldSpec(_coerce_non_negative_int),
        'minutes_played': FieldSpec(_coerce_non_negative_int),
        'goals': FieldSpec(_coerce_non_negative_int),
        'assists': FieldSpec(_coerce_non_negative_int),
        'shots': FieldSpec(_coerce_non_negative_int),
        'xg': FieldSpec(_coerce_non_negative_decimal),
        'xa': FieldSpec(_coerce_non_negative_decimal),
        'npg': FieldSpec(_coerce_non_negative_decimal),
        'npxg': FieldSpec(_coerce_non_negative_decimal),
        'xg_chain': FieldSpec(_coerce_non_negative_decimal),
        'xg_buildup': FieldSpec(_coerce_non_negative_decimal),
        'yellow_cards': FieldSpec(_coerce_non_negative_int),
        'red_cards': FieldSpec(_coerce_non_negative_int),
        'key_passes': FieldSpec(_coerce_non_negative_int),
    },
    required_header_groups=(
        PLAYER_SEASON_IDENTIFIER_FIELDS,
        PLAYER_SEASON_STAT_FIELDS,
    ),
    required_value_groups=(
        PLAYER_SEASON_IDENTIFIER_FIELDS,
        PLAYER_SEASON_STAT_FIELDS,
    ),
)

SQUAD_METRIC_SCHEMA = ImportSchema(
    target_model='ClubSeasonEnrichment',
    fields={
        'provider': FieldSpec(_coerce_provider, required=True),
        'season_label': FieldSpec(_coerce_non_empty_string, required=True, aliases=('season',)),
        'competition_code': FieldSpec(_coerce_upper_string),
        'competition_name': FieldSpec(_coerce_string),
        'external_team_id': FieldSpec(_coerce_string),
        'matches_played': FieldSpec(_coerce_non_negative_int),
        'wins': FieldSpec(_coerce_non_negative_int),
        'draws': FieldSpec(_coerce_non_negative_int),
        'losses': FieldSpec(_coerce_non_negative_int),
        'goals_for': FieldSpec(_coerce_non_negative_int),
        'goals_against': FieldSpec(_coerce_non_negative_int),
        'xg': FieldSpec(_coerce_non_negative_decimal),
        'xga': FieldSpec(_coerce_non_negative_decimal),
        'npxg': FieldSpec(_coerce_non_negative_decimal),
        'ppda': FieldSpec(_coerce_non_negative_decimal),
    },
    required_header_groups=(SQUAD_METRIC_FIELDS,),
    required_value_groups=(SQUAD_METRIC_FIELDS,),
)

IMPORT_SCHEMAS = {
    ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE: PLAYER_PROFILE_SCHEMA,
    ClubImportJob.ImportType.PLAYER_SEASON_STATS: PLAYER_SEASON_SCHEMA,
    ClubImportJob.ImportType.SQUAD_METRICS: SQUAD_METRIC_SCHEMA,
}

MATCHED_ROW_STATUS = 'matched'


def persist_import_preview(job: ClubImportJob) -> ClubImportJob:
    job.mark_validating()

    try:
        validation_result = validate_import_job(job)
        preview_payload = build_import_preview_payload(job, validation_result)

        counts = preview_payload['counts']

        job.mark_preview_ready(
            preview_payload=preview_payload,
            row_count=counts['total_rows'],
            valid_row_count=counts['valid_rows'],
            warning_count=counts['warning_count'],
        )
        return job

    except ClubImportValidationError as exc:
        error_summary = {
            'stage': 'preview',
            'message': str(exc),
            'details': exc.details,
        }
        report_payload = build_failed_preview_report(
            job,
            message=str(exc),
            details=exc.details,
        )
        job.mark_failed(
            error_summary=error_summary,
            report_payload=report_payload,
            clear_preview=True,
        )
        return job

    except Exception as exc:
        error_summary = {
            'stage': 'preview',
            'message': str(exc),
            'details': {},
        }
        report_payload = build_failed_preview_report(
            job,
            message=str(exc),
            details={},
        )
        job.mark_failed(
            error_summary=error_summary,
            report_payload=report_payload,
            clear_preview=True,
        )
        return job


def build_failed_preview_report(
    job: ClubImportJob,
    *,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'job_id': job.id,
        'club_id': job.club_id,
        'source_resource_id': job.source_resource_id,
        'import_type': job.import_type,
        'stage': 'preview',
        'status': 'failed',
        'generated_at': timezone.now().isoformat(),
        'counts': {
            'total_rows': 0,
            'valid_rows': 0,
            'skipped_rows': 0,
            'unmatched_rows': 0,
            'ambiguous_rows': 0,
            'invalid_rows': 0,
            'warning_count': 0,
        },
        'errors': [
            {
                'message': message,
                'details': details or {},
            }
        ],
    }


def build_import_preview_payload(
    job: ClubImportJob,
    validation_result: ImportValidationResult,
) -> dict[str, Any]:
    preview_rows = [
        build_preview_row_payload(job, row)
        for row in validation_result.rows
    ]

    counts = {
        'total_rows': validation_result.total_rows,
        'valid_rows': validation_result.valid_row_count,
        'skipped_rows': validation_result.skipped_row_count,
        'unmatched_rows': validation_result.unmatched_row_count,
        'ambiguous_rows': validation_result.ambiguous_row_count,
        'invalid_rows': validation_result.invalid_row_count,
        'warning_count': validation_result.warning_count,
    }

    return {
        'job_id': job.id,
        'club_id': job.club_id,
        'source_resource_id': job.source_resource_id,
        'import_type': job.import_type,
        'generated_at': timezone.now().isoformat(),
        'counts': counts,
        'can_commit': (
            job.import_type != ClubImportJob.ImportType.OTHER and
            counts['valid_rows'] > 0
        ),
        'rows': preview_rows,
        'raw_preview': validation_result.is_raw_preview,
    }


def build_preview_row_payload(
    job: ClubImportJob,
    row: ImportRowResult,
) -> dict[str, Any]:
    payload = row.to_dict()

    if row.status != MATCHED_ROW_STATUS:
        payload['record_action'] = None
        payload['target_record_id'] = None
        payload['current_values'] = {}
        payload['proposed_changes'] = {}
        return payload

    if job.import_type == ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE:
        preview_context = _build_club_player_preview_context(row)

    elif job.import_type == ClubImportJob.ImportType.PLAYER_SEASON_STATS:
        preview_context = _build_player_season_preview_context(job, row)

    elif job.import_type == ClubImportJob.ImportType.SQUAD_METRICS:
        preview_context = _build_squad_metrics_preview_context(job, row)

    else:
        preview_context = {
            'record_action': None,
            'target_record_id': None,
            'current_values': {},
            'proposed_changes': {},
        }

    payload.update(preview_context)
    return payload


def _build_club_player_preview_context(row: ImportRowResult) -> dict[str, Any]:
    club_player = ClubPlayer.objects.get(pk=row.target_id)

    updatable_fields = [
        'first_name',
        'last_name',
        'display_name',
        'squad_number',
        'primary_position',
        'secondary_position',
        'preferred_foot',
        'date_of_birth',
        'height_cm',
        'is_active',
        'is_public',
    ]

    current_values, proposed_changes = _compare_model_fields(
        instance=club_player,
        incoming_data=row.normalised_data,
        field_names=updatable_fields,
    )

    record_action = 'update' if proposed_changes else 'no_change'

    return {
        'record_action': record_action,
        'target_record_id': club_player.id,
        'current_values': current_values,
        'proposed_changes': proposed_changes,
    }


def _build_player_season_preview_context(
    job: ClubImportJob,
    row: ImportRowResult,
) -> dict[str, Any]:
    existing = PlayerSeasonEnrichment.objects.filter(
        player_id=row.target_id,
        club_id=job.club_id,
        provider=row.normalised_data['provider'],
        season_label=row.normalised_data['season_label'],
        competition_code=row.normalised_data.get('competition_code', ''),
        external_team_id=row.normalised_data.get('external_team_id', ''),
    ).first()

    comparable_fields = [
        'provider',
        'season_label',
        'competition_code',
        'competition_name',
        'external_player_id',
        'external_team_id',
        'matches_played',
        'minutes_played',
        'goals',
        'assists',
        'shots',
        'xg',
        'xa',
        'npg',
        'npxg',
        'xg_chain',
        'xg_buildup',
        'yellow_cards',
        'red_cards',
        'key_passes',
    ]

    if existing is None:
        current_values = {field_name: None for field_name in comparable_fields}
        proposed_changes = {
            field_name: {
                'from': None,
                'to': _serialise_preview_value(row.normalised_data.get(field_name)),
            }
            for field_name in comparable_fields
            if field_name in row.normalised_data
        }
        record_action = 'create'
        target_record_id = None
    else:
        current_values, proposed_changes = _compare_model_fields(
            instance=existing,
            incoming_data=row.normalised_data,
            field_names=comparable_fields,
        )
        record_action = 'update' if proposed_changes else 'no_change'
        target_record_id = existing.id

    return {
        'record_action': record_action,
        'target_record_id': target_record_id,
        'current_values': current_values,
        'proposed_changes': proposed_changes,
    }


def _build_squad_metrics_preview_context(
    job: ClubImportJob,
    row: ImportRowResult,
) -> dict[str, Any]:
    existing = ClubSeasonEnrichment.objects.filter(
        club_id=job.club_id,
        provider=row.normalised_data['provider'],
        season_label=row.normalised_data['season_label'],
        competition_code=row.normalised_data.get('competition_code', ''),
    ).first()

    comparable_fields = [
        'provider',
        'season_label',
        'competition_code',
        'competition_name',
        'external_team_id',
        'matches_played',
        'wins',
        'draws',
        'losses',
        'goals_for',
        'goals_against',
        'xg',
        'xga',
        'npxg',
        'ppda',
    ]

    if existing is None:
        current_values = {field_name: None for field_name in comparable_fields}
        proposed_changes = {
            field_name: {
                'from': None,
                'to': _serialise_preview_value(row.normalised_data.get(field_name)),
            }
            for field_name in comparable_fields
            if field_name in row.normalised_data
        }
        record_action = 'create'
        target_record_id = None
    else:
        current_values, proposed_changes = _compare_model_fields(
            instance=existing,
            incoming_data=row.normalised_data,
            field_names=comparable_fields,
        )
        record_action = 'update' if proposed_changes else 'no_change'
        target_record_id = existing.id

    return {
        'record_action': record_action,
        'target_record_id': target_record_id,
        'current_values': current_values,
        'proposed_changes': proposed_changes,
    }


def _compare_model_fields(
    *,
    instance,
    incoming_data: dict[str, Any],
    field_names: list[str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    current_values: dict[str, Any] = {}
    proposed_changes: dict[str, dict[str, Any]] = {}

    for field_name in field_names:
        current_value = _serialise_preview_value(getattr(instance, field_name, None))
        current_values[field_name] = current_value

        if field_name not in incoming_data:
            continue

        new_value = _serialise_preview_value(incoming_data[field_name])

        if current_value != new_value:
            proposed_changes[field_name] = {
                'from': current_value,
                'to': new_value,
            }

    return current_values, proposed_changes

def commit_import_job(job: ClubImportJob, *, confirmed_by) -> ClubImportJob:
    membership = ClubMembership.objects.filter(
        user=confirmed_by,
        club=job.club,
        is_active=True,
    ).first()

    if membership is None or not membership.can_manage_members():
        raise ClubImportCommitError(
            'Only owner/admin members can confirm and commit this import job.'
        )

    if job.status != ClubImportJob.Status.PREVIEW_READY:
        raise ClubImportCommitError(
            'Only preview_ready import jobs can be committed.'
        )

    preview_payload = job.preview_payload or {}
    preview_rows = preview_payload.get('rows', [])
    preview_counts = preview_payload.get('counts', {})

    if not preview_rows:
        raise ClubImportCommitError(
            'This import job does not have a persisted preview to commit.'
        )

    matched_rows = [
        row for row in preview_rows
        if row.get('status') == MATCHED_ROW_STATUS
    ]

    if not matched_rows:
        raise ClubImportCommitError(
            'This import job does not contain any valid matched rows to commit.'
        )

    non_committable_row_count = (
        preview_counts.get('skipped_rows', 0) +
        preview_counts.get('unmatched_rows', 0) +
        preview_counts.get('ambiguous_rows', 0) +
        preview_counts.get('invalid_rows', 0)
    )

    try:
        with transaction.atomic():
            job.mark_confirmed()
            job.mark_processing()

            created_rows = 0
            updated_rows = 0
            no_change_rows = 0

            for preview_row in matched_rows:
                record_action = preview_row.get('record_action')

                if record_action == 'no_change':
                    no_change_rows += 1
                    continue

                _commit_preview_row(job, preview_row)

                if record_action == 'create':
                    created_rows += 1
                elif record_action == 'update':
                    updated_rows += 1
                else:
                    raise ClubImportCommitError(
                        f'Unsupported record_action during commit: {record_action}'
                    )

            imported_row_count = created_rows + updated_rows
            skipped_row_count = non_committable_row_count + no_change_rows
            failed_row_count = 0

            report_payload = build_completed_commit_report(
                job,
                preview_payload=preview_payload,
                created_rows=created_rows,
                updated_rows=updated_rows,
                no_change_rows=no_change_rows,
                imported_row_count=imported_row_count,
                skipped_row_count=skipped_row_count,
                failed_row_count=failed_row_count,
                confirmed_by=confirmed_by,
            )

            job.mark_completed(
                imported_row_count=imported_row_count,
                skipped_row_count=skipped_row_count,
                failed_row_count=failed_row_count,
                report_payload=report_payload,
            )

    except Exception as exc:
        error_summary = {
            'stage': 'commit',
            'message': str(exc),
            'details': {},
        }
        report_payload = build_failed_commit_report(
            job,
            preview_payload=preview_payload,
            message=str(exc),
            confirmed_by=confirmed_by,
            failed_row_count=len(matched_rows),
            skipped_row_count=non_committable_row_count,
        )

        job.mark_commit_failed(
            imported_row_count=0,
            skipped_row_count=non_committable_row_count,
            failed_row_count=len(matched_rows),
            error_summary=error_summary,
            report_payload=report_payload,
        )

        if isinstance(exc, ClubImportCommitError):
            raise

        raise ClubImportCommitError(
            f'Import commit failed and was rolled back atomically: {exc}'
        ) from exc

    return job


def build_completed_commit_report(
    job: ClubImportJob,
    *,
    preview_payload: dict[str, Any],
    created_rows: int,
    updated_rows: int,
    no_change_rows: int,
    imported_row_count: int,
    skipped_row_count: int,
    failed_row_count: int,
    confirmed_by,
) -> dict[str, Any]:
    preview_counts = preview_payload.get('counts', {})

    return {
        'job_id': job.id,
        'club_id': job.club_id,
        'source_resource_id': job.source_resource_id,
        'import_type': job.import_type,
        'stage': 'commit',
        'status': 'completed',
        'generated_at': timezone.now().isoformat(),
        'confirmed_by_user_id': confirmed_by.id,
        'counts': {
            'total_rows': preview_counts.get('total_rows', 0),
            'valid_rows': preview_counts.get('valid_rows', 0),
            'imported_rows': imported_row_count,
            'created_rows': created_rows,
            'updated_rows': updated_rows,
            'no_change_rows': no_change_rows,
            'skipped_rows': skipped_row_count,
            'failed_rows': failed_row_count,
        },
    }


def build_failed_commit_report(
    job: ClubImportJob,
    *,
    preview_payload: dict[str, Any],
    message: str,
    confirmed_by,
    failed_row_count: int,
    skipped_row_count: int,
) -> dict[str, Any]:
    preview_counts = preview_payload.get('counts', {})

    return {
        'job_id': job.id,
        'club_id': job.club_id,
        'source_resource_id': job.source_resource_id,
        'import_type': job.import_type,
        'stage': 'commit',
        'status': 'failed',
        'generated_at': timezone.now().isoformat(),
        'confirmed_by_user_id': confirmed_by.id,
        'counts': {
            'total_rows': preview_counts.get('total_rows', 0),
            'valid_rows': preview_counts.get('valid_rows', 0),
            'imported_rows': 0,
            'skipped_rows': skipped_row_count,
            'failed_rows': failed_row_count,
        },
        'errors': [
            {
                'message': message,
                'details': {},
            }
        ],
    }


def _commit_preview_row(job: ClubImportJob, preview_row: dict[str, Any]) -> None:
    normalised_data = _hydrate_preview_row_normalised_data(job, preview_row)
    record_action = preview_row.get('record_action')
    target_record_id = preview_row.get('target_record_id')
    target_id = preview_row.get('target_id')

    if job.import_type == ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE:
        _apply_player_profile_update_row(
            job=job,
            normalised_data=normalised_data,
            target_record_id=target_record_id,
            record_action=record_action,
        )
        return

    if job.import_type == ClubImportJob.ImportType.PLAYER_SEASON_STATS:
        _apply_player_season_row(
            job=job,
            normalised_data=normalised_data,
            target_record_id=target_record_id,
            target_player_id=target_id,
            record_action=record_action,
        )
        return

    if job.import_type == ClubImportJob.ImportType.SQUAD_METRICS:
        _apply_squad_metrics_row(
            job=job,
            normalised_data=normalised_data,
            target_record_id=target_record_id,
            record_action=record_action,
        )
        return

    raise ClubImportCommitError(
        f'Unsupported import_type during commit: {job.import_type}'
    )


def _hydrate_preview_row_normalised_data(
    job: ClubImportJob,
    preview_row: dict[str, Any],
) -> dict[str, Any]:
    schema = IMPORT_SCHEMAS[job.import_type]
    hydrated: dict[str, Any] = {}

    for field_name, value in (preview_row.get('normalised_data') or {}).items():
        if value is None:
            hydrated[field_name] = None
            continue

        if field_name not in schema.fields:
            continue

        hydrated[field_name] = schema.fields[field_name].coercer(value)

    return hydrated


def _apply_player_profile_update_row(
    *,
    job: ClubImportJob,
    normalised_data: dict[str, Any],
    target_record_id: int | None,
    record_action: str | None,
) -> None:
    if record_action != 'update':
        raise ClubImportCommitError(
            f'player_profile_update rows only support update, got {record_action}.'
        )

    if target_record_id is None:
        raise ClubImportCommitError(
            'player_profile_update row is missing target_record_id.'
        )

    club_player = ClubPlayer.objects.get(
        pk=target_record_id,
        club_id=job.club_id,
    )

    updatable_fields = [
        'first_name',
        'last_name',
        'display_name',
        'squad_number',
        'primary_position',
        'secondary_position',
        'preferred_foot',
        'date_of_birth',
        'height_cm',
        'is_active',
        'is_public',
    ]

    for field_name in updatable_fields:
        if field_name in normalised_data:
            setattr(club_player, field_name, normalised_data[field_name])

    club_player.save()


def _apply_player_season_row(
    *,
    job: ClubImportJob,
    normalised_data: dict[str, Any],
    target_record_id: int | None,
    target_player_id: int | None,
    record_action: str | None,
) -> None:
    if record_action not in {'create', 'update'}:
        raise ClubImportCommitError(
            f'player_season_stats rows only support create/update, got {record_action}.'
        )

    if target_player_id is None:
        raise ClubImportCommitError(
            'player_season_stats row is missing target player id.'
        )

    if record_action == 'update':
        if target_record_id is None:
            raise ClubImportCommitError(
                'player_season_stats update row is missing target_record_id.'
            )
        instance = PlayerSeasonEnrichment.objects.get(
            pk=target_record_id,
            player_id=target_player_id,
        )
    else:
        instance = PlayerSeasonEnrichment(
            player_id=target_player_id,
            club_id=job.club_id,
        )

    instance.provider = normalised_data['provider']
    instance.season_label = normalised_data['season_label']
    instance.competition_code = normalised_data.get('competition_code', '') or ''
    instance.competition_name = normalised_data.get('competition_name', '') or ''
    instance.external_player_id = normalised_data.get('external_player_id', '') or ''
    instance.external_team_id = normalised_data.get('external_team_id', '') or ''

    stat_fields = [
        'matches_played',
        'minutes_played',
        'goals',
        'assists',
        'shots',
        'xg',
        'xa',
        'npg',
        'npxg',
        'xg_chain',
        'xg_buildup',
        'yellow_cards',
        'red_cards',
        'key_passes',
    ]

    for field_name in stat_fields:
        if field_name in normalised_data:
            setattr(instance, field_name, normalised_data[field_name])

    instance.save()


def _apply_squad_metrics_row(
    *,
    job: ClubImportJob,
    normalised_data: dict[str, Any],
    target_record_id: int | None,
    record_action: str | None,
) -> None:
    if record_action not in {'create', 'update'}:
        raise ClubImportCommitError(
            f'squad_metrics rows only support create/update, got {record_action}.'
        )

    if record_action == 'update':
        if target_record_id is None:
            raise ClubImportCommitError(
                'squad_metrics update row is missing target_record_id.'
            )
        instance = ClubSeasonEnrichment.objects.get(
            pk=target_record_id,
            club_id=job.club_id,
        )
    else:
        instance = ClubSeasonEnrichment(
            club_id=job.club_id,
        )

    instance.provider = normalised_data['provider']
    instance.season_label = normalised_data['season_label']
    instance.competition_code = normalised_data.get('competition_code', '') or ''
    instance.competition_name = normalised_data.get('competition_name', '') or ''
    instance.external_team_id = normalised_data.get('external_team_id', '') or ''

    stat_fields = [
        'matches_played',
        'wins',
        'draws',
        'losses',
        'goals_for',
        'goals_against',
        'xg',
        'xga',
        'npxg',
        'ppda',
    ]

    for field_name in stat_fields:
        if field_name in normalised_data:
            setattr(instance, field_name, normalised_data[field_name])

    instance.save()