from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db.models import Q, QuerySet

from apps.playerdata.models import ClubSeasonEnrichment, PlayerSeasonEnrichment
from services.playerdata.helpers import clean_optional_str, resolve_ordering


def _normalise_season_label(
    *,
    season_label: str | None = None,
    season: str | None = None,
) -> str | None:
    return clean_optional_str(season_label) or clean_optional_str(season)


def _normalise_order_by(
    *,
    order_by: str | None = None,
    ordering: str | None = None,
    default: str,
) -> str:
    cleaned_order_by = clean_optional_str(order_by)
    if cleaned_order_by:
        return cleaned_order_by

    cleaned_ordering = clean_optional_str(ordering)
    if cleaned_ordering:
        return cleaned_ordering

    return default


def _build_provider_coverage_dict(
    *,
    provider: str,
    last_synced_at: datetime | None,
    matches_sampled: int | None = None,
    minutes_sampled: int | None = None,
) -> dict[str, Any]:
    coverage_notes: list[str] = []

    if last_synced_at is None:
        coverage_status = "unknown"
        freshness_label = "unknown"
        coverage_notes.append("No last_synced_at timestamp is available.")
    else:
        coverage_status = "available"
        freshness_label = "synced"

    return {
        "provider": provider,
        "has_data": True,
        "coverage_status": coverage_status,
        "freshness_label": freshness_label,
        "source_updated_at": None,
        "last_synced_at": last_synced_at,
        "matches_sampled": matches_sampled,
        "minutes_sampled": minutes_sampled,
        "coverage_notes": coverage_notes,
    }


def _format_decimal(value: Decimal | None, decimal_places: int = 2) -> str | None:
    if value is None:
        return None
    return f"{value:.{decimal_places}f}"


def _build_metric(
    *,
    key: str,
    label: str,
    value: int | float | Decimal | None,
    unit: str | None = None,
) -> dict[str, Any]:
    if isinstance(value, Decimal):
        formatted_value = _format_decimal(value)
        serialisable_value: float | int | None = float(value)
    else:
        formatted_value = None if value is None else str(value)
        serialisable_value = value

    return {
        "key": key,
        "label": label,
        "value": serialisable_value,
        "formatted_value": formatted_value,
        "unit": unit,
        "rank": None,
        "percentile": None,
        "sample_size": None,
        "is_available": value is not None,
    }


def _build_player_explanation(
    *,
    matches_played: int,
    minutes_played: int,
    goals: int,
    assists: int,
    xg: Decimal | None,
    xa: Decimal | None,
) -> dict[str, Any]:
    strengths: list[str] = []
    watchouts: list[str] = []
    notes: list[str] = []

    if goals > 0:
        strengths.append(f"Recorded {goals} goal{'s' if goals != 1 else ''}.")
    if assists > 0:
        strengths.append(f"Recorded {assists} assist{'s' if assists != 1 else ''}.")
    if xg is not None:
        notes.append(f"xG value stored for this season: {_format_decimal(xg)}.")
    if xa is not None:
        notes.append(f"xA value stored for this season: {_format_decimal(xa)}.")
    if minutes_played < 300:
        watchouts.append("Sample size is small based on minutes played.")

    summary_bits = [
        f"{matches_played} matches",
        f"{minutes_played} minutes",
        f"{goals} goals",
        f"{assists} assists",
    ]
    summary = ", ".join(summary_bits) + "."

    return {
        "headline": "Deterministic season summary",
        "summary": summary,
        "strengths": strengths,
        "watchouts": watchouts,
        "notes": notes,
    }


def _build_club_explanation(
    *,
    matches_played: int,
    wins: int,
    draws: int,
    losses: int,
    goals_for: int,
    goals_against: int,
    xg: Decimal | None,
    xga: Decimal | None,
) -> dict[str, Any]:
    strengths: list[str] = []
    watchouts: list[str] = []
    notes: list[str] = []

    if wins > losses:
        strengths.append("Wins exceed losses in the stored season summary.")
    if goals_for > goals_against:
        strengths.append("Goals scored exceed goals conceded.")
    if losses > wins:
        watchouts.append("Losses exceed wins in the stored season summary.")
    if xg is not None:
        notes.append(f"xG value stored for this season: {_format_decimal(xg)}.")
    if xga is not None:
        notes.append(f"xGA value stored for this season: {_format_decimal(xga)}.")

    summary = (
        f"{matches_played} matches, {wins} wins, {draws} draws, "
        f"{losses} losses, {goals_for} goals for, {goals_against} against."
    )

    return {
        "headline": "Deterministic club season summary",
        "summary": summary,
        "strengths": strengths,
        "watchouts": watchouts,
        "notes": notes,
    }


@dataclass(frozen=True)
class PlayerSeasonEnrichmentRecord:
    enrichment_id: int
    player_id: int
    player_name: str
    primary_position: str
    secondary_positions: list[str]
    club_id: int | None
    club_name: str | None
    provider: str
    season_label: str
    competition_code: str
    competition_name: str
    matches_played: int
    minutes_played: int
    goals: int
    assists: int
    shots: int
    xg: Decimal | None
    xa: Decimal | None
    npg: Decimal | None
    npxg: Decimal | None
    key_passes: int
    last_synced_at: datetime | None
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def player(self) -> dict[str, Any]:
        return {
            "id": self.player_id,
            "full_name": self.player_name,
            "display_name": self.player_name,
            "short_name": self.player_name,
            "position": self.primary_position,
            "nationality": None,
            "age": None,
            "photo_url": None,
        }

    @property
    def club(self) -> dict[str, Any] | None:
        if self.club_id is None and not self.club_name:
            return None

        return {
            "id": self.club_id,
            "name": self.club_name,
            "short_name": self.club_name,
            "crest_url": None,
        }

    @property
    def context(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "season": self.season_label,
            "competition_code": self.competition_code,
            "competition_name": self.competition_name,
        }

    @property
    def metrics(self) -> list[dict[str, Any]]:
        return [
            _build_metric(key="matches_played", label="Matches played", value=self.matches_played),
            _build_metric(key="minutes_played", label="Minutes played", value=self.minutes_played),
            _build_metric(key="goals", label="Goals", value=self.goals),
            _build_metric(key="assists", label="Assists", value=self.assists),
            _build_metric(key="shots", label="Shots", value=self.shots),
            _build_metric(key="xg", label="xG", value=self.xg),
            _build_metric(key="xa", label="xA", value=self.xa),
            _build_metric(key="npg", label="Non-penalty goals", value=self.npg),
            _build_metric(key="npxg", label="npxG", value=self.npxg),
            _build_metric(key="key_passes", label="Key passes", value=self.key_passes),
        ]

    @property
    def key_metrics(self) -> list[dict[str, Any]]:
        return [
            _build_metric(key="minutes_played", label="Minutes played", value=self.minutes_played),
            _build_metric(key="goals", label="Goals", value=self.goals),
            _build_metric(key="assists", label="Assists", value=self.assists),
            _build_metric(key="xg", label="xG", value=self.xg),
            _build_metric(key="xa", label="xA", value=self.xa),
        ]

    @property
    def explanation(self) -> dict[str, Any]:
        return _build_player_explanation(
            matches_played=self.matches_played,
            minutes_played=self.minutes_played,
            goals=self.goals,
            assists=self.assists,
            xg=self.xg,
            xa=self.xa,
        )

    @property
    def explanation_snippet(self) -> str:
        return (
            f"{self.matches_played} matches, {self.minutes_played} minutes, "
            f"{self.goals} goals, {self.assists} assists."
        )

    @property
    def provider_coverage(self) -> dict[str, Any]:
        return _build_provider_coverage_dict(
            provider=self.provider,
            last_synced_at=self.last_synced_at,
            matches_sampled=self.matches_played,
            minutes_sampled=self.minutes_played,
        )

    @property
    def has_summary_data(self) -> bool:
        return True

    @property
    def has_enrichment_data(self) -> bool:
        return True

    @property
    def missing_reasons(self) -> list[str]:
        return []


@dataclass(frozen=True)
class ClubSeasonEnrichmentRecord:
    enrichment_id: int
    club_id: int
    club_name: str
    provider: str
    season_label: str
    competition_code: str
    competition_name: str
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    xg: Decimal | None
    xga: Decimal | None
    npxg: Decimal | None
    ppda: Decimal | None
    last_synced_at: datetime | None
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def club(self) -> dict[str, Any]:
        return {
            "id": self.club_id,
            "name": self.club_name,
            "short_name": self.club_name,
            "crest_url": None,
        }

    @property
    def context(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "season": self.season_label,
            "competition_code": self.competition_code,
            "competition_name": self.competition_name,
        }

    @property
    def metrics(self) -> list[dict[str, Any]]:
        return [
            _build_metric(key="matches_played", label="Matches played", value=self.matches_played),
            _build_metric(key="wins", label="Wins", value=self.wins),
            _build_metric(key="draws", label="Draws", value=self.draws),
            _build_metric(key="losses", label="Losses", value=self.losses),
            _build_metric(key="goals_for", label="Goals for", value=self.goals_for),
            _build_metric(key="goals_against", label="Goals against", value=self.goals_against),
            _build_metric(key="xg", label="xG", value=self.xg),
            _build_metric(key="xga", label="xGA", value=self.xga),
            _build_metric(key="npxg", label="npxG", value=self.npxg),
            _build_metric(key="ppda", label="PPDA", value=self.ppda),
        ]

    @property
    def explanation(self) -> dict[str, Any]:
        return _build_club_explanation(
            matches_played=self.matches_played,
            wins=self.wins,
            draws=self.draws,
            losses=self.losses,
            goals_for=self.goals_for,
            goals_against=self.goals_against,
            xg=self.xg,
            xga=self.xga,
        )

    @property
    def provider_coverage(self) -> dict[str, Any]:
        return _build_provider_coverage_dict(
            provider=self.provider,
            last_synced_at=self.last_synced_at,
            matches_sampled=self.matches_played,
            minutes_sampled=None,
        )

    @property
    def has_summary_data(self) -> bool:
        return True

    @property
    def missing_reasons(self) -> list[str]:
        return []


PLAYER_ORDERING_FIELDS: dict[str, tuple[str, ...]] = {
    "last_synced_at": ("last_synced_at", "updated_at", "id"),
    "updated_at": ("updated_at", "id"),
    "season_label": ("season_label", "updated_at", "id"),
    "minutes_played": ("minutes_played", "updated_at", "id"),
    "matches_played": ("matches_played", "updated_at", "id"),
    "goals": ("goals", "updated_at", "id"),
    "assists": ("assists", "updated_at", "id"),
    "shots": ("shots", "updated_at", "id"),
    "xg": ("xg", "updated_at", "id"),
    "xa": ("xa", "updated_at", "id"),
    "npg": ("npg", "updated_at", "id"),
    "npxg": ("npxg", "updated_at", "id"),
    "key_passes": ("key_passes", "updated_at", "id"),
    "player_name": ("player__display_name", "player__last_name", "player__first_name", "id"),
    "club_name": ("club__name", "player__display_name", "id"),
}

CLUB_ORDERING_FIELDS: dict[str, tuple[str, ...]] = {
    "last_synced_at": ("last_synced_at", "updated_at", "id"),
    "updated_at": ("updated_at", "id"),
    "season_label": ("season_label", "updated_at", "id"),
    "matches_played": ("matches_played", "updated_at", "id"),
    "wins": ("wins", "updated_at", "id"),
    "draws": ("draws", "updated_at", "id"),
    "losses": ("losses", "updated_at", "id"),
    "goals_for": ("goals_for", "updated_at", "id"),
    "goals_against": ("goals_against", "updated_at", "id"),
    "xg": ("xg", "updated_at", "id"),
    "xga": ("xga", "updated_at", "id"),
    "npxg": ("npxg", "updated_at", "id"),
    "ppda": ("ppda", "updated_at", "id"),
    "club_name": ("club__name", "id"),
}


def _player_display_name(enrichment: PlayerSeasonEnrichment) -> str:
    player = enrichment.player

    display_name = getattr(player, "display_name", "") or ""
    if display_name:
        return display_name

    full_name = getattr(player, "full_name", "") or ""
    if full_name:
        return full_name

    first_name = getattr(player, "first_name", "") or ""
    last_name = getattr(player, "last_name", "") or ""
    return f"{first_name} {last_name}".strip()


def _player_secondary_positions(enrichment: PlayerSeasonEnrichment) -> list[str]:
    player = enrichment.player
    secondary_positions = getattr(player, "secondary_positions", None)

    if secondary_positions is None:
        return []

    return list(secondary_positions or [])


def _player_queryset() -> QuerySet[PlayerSeasonEnrichment]:
    return PlayerSeasonEnrichment.objects.select_related("player", "club")


def _club_queryset() -> QuerySet[ClubSeasonEnrichment]:
    return ClubSeasonEnrichment.objects.select_related("club")


def _apply_player_filters(
    queryset: QuerySet[PlayerSeasonEnrichment],
    *,
    player_id: int | None = None,
    club_id: int | None = None,
    provider: str | None = None,
    season_label: str | None = None,
    season: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    position: str | None = None,
    search: str | None = None,
    min_minutes: int | None = None,
    min_goals: int | None = None,
    min_assists: int | None = None,
    min_xg: Decimal | float | str | None = None,
    min_xa: Decimal | float | str | None = None,
) -> QuerySet[PlayerSeasonEnrichment]:
    if player_id is not None:
        queryset = queryset.filter(player_id=player_id)

    if club_id is not None:
        queryset = queryset.filter(club_id=club_id)

    provider = clean_optional_str(provider)
    if provider:
        queryset = queryset.filter(provider=provider)

    resolved_season_label = _normalise_season_label(
        season_label=season_label,
        season=season,
    )
    if resolved_season_label:
        queryset = queryset.filter(season_label=resolved_season_label)

    competition_code = clean_optional_str(competition_code)
    if competition_code:
        queryset = queryset.filter(competition_code=competition_code)

    competition_name = clean_optional_str(competition_name)
    if competition_name:
        queryset = queryset.filter(competition_name=competition_name)

    position = clean_optional_str(position)
    if position:
        queryset = queryset.filter(
            Q(player__primary_position=position)
            | Q(player__secondary_positions__contains=[position])
        )

    search = clean_optional_str(search)
    if search:
        queryset = queryset.filter(
            Q(player__display_name__icontains=search)
            | Q(player__full_name__icontains=search)
            | Q(player__first_name__icontains=search)
            | Q(player__last_name__icontains=search)
            | Q(club__name__icontains=search)
        )

    if min_minutes is not None:
        queryset = queryset.filter(minutes_played__gte=min_minutes)

    if min_goals is not None:
        queryset = queryset.filter(goals__gte=min_goals)

    if min_assists is not None:
        queryset = queryset.filter(assists__gte=min_assists)

    if min_xg is not None:
        queryset = queryset.filter(xg__gte=min_xg)

    if min_xa is not None:
        queryset = queryset.filter(xa__gte=min_xa)

    return queryset


def _apply_club_filters(
    queryset: QuerySet[ClubSeasonEnrichment],
    *,
    club_id: int | None = None,
    provider: str | None = None,
    season_label: str | None = None,
    season: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
) -> QuerySet[ClubSeasonEnrichment]:
    if club_id is not None:
        queryset = queryset.filter(club_id=club_id)

    provider = clean_optional_str(provider)
    if provider:
        queryset = queryset.filter(provider=provider)

    resolved_season_label = _normalise_season_label(
        season_label=season_label,
        season=season,
    )
    if resolved_season_label:
        queryset = queryset.filter(season_label=resolved_season_label)

    competition_code = clean_optional_str(competition_code)
    if competition_code:
        queryset = queryset.filter(competition_code=competition_code)

    competition_name = clean_optional_str(competition_name)
    if competition_name:
        queryset = queryset.filter(competition_name=competition_name)

    return queryset


def _to_player_record(enrichment: PlayerSeasonEnrichment) -> PlayerSeasonEnrichmentRecord:
    club = enrichment.club

    return PlayerSeasonEnrichmentRecord(
        enrichment_id=enrichment.id,
        player_id=enrichment.player_id,
        player_name=_player_display_name(enrichment),
        primary_position=getattr(enrichment.player, "primary_position", "") or "",
        secondary_positions=_player_secondary_positions(enrichment),
        club_id=club.id if club else None,
        club_name=club.name if club else None,
        provider=enrichment.provider,
        season_label=enrichment.season_label,
        competition_code=enrichment.competition_code or "",
        competition_name=enrichment.competition_name or "",
        matches_played=enrichment.matches_played,
        minutes_played=enrichment.minutes_played,
        goals=enrichment.goals,
        assists=enrichment.assists,
        shots=enrichment.shots,
        xg=enrichment.xg,
        xa=enrichment.xa,
        npg=enrichment.npg,
        npxg=enrichment.npxg,
        key_passes=enrichment.key_passes,
        last_synced_at=enrichment.last_synced_at,
        updated_at=enrichment.updated_at,
    )


def _to_club_record(enrichment: ClubSeasonEnrichment) -> ClubSeasonEnrichmentRecord:
    return ClubSeasonEnrichmentRecord(
        enrichment_id=enrichment.id,
        club_id=enrichment.club_id,
        club_name=enrichment.club.name,
        provider=enrichment.provider,
        season_label=enrichment.season_label,
        competition_code=enrichment.competition_code or "",
        competition_name=enrichment.competition_name or "",
        matches_played=enrichment.matches_played,
        wins=enrichment.wins,
        draws=enrichment.draws,
        losses=enrichment.losses,
        goals_for=enrichment.goals_for,
        goals_against=enrichment.goals_against,
        xg=enrichment.xg,
        xga=enrichment.xga,
        npxg=enrichment.npxg,
        ppda=enrichment.ppda,
        last_synced_at=enrichment.last_synced_at,
        updated_at=enrichment.updated_at,
    )


def get_player_season_enrichment(
    player_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    club_id: int | None = None,
) -> PlayerSeasonEnrichmentRecord | None:
    queryset = _apply_player_filters(
        _player_queryset(),
        player_id=player_id,
        club_id=club_id,
        provider=provider,
        season_label=season_label,
        season=season,
        competition_code=competition_code,
        competition_name=competition_name,
    ).order_by("-season_label", "-last_synced_at", "-updated_at", "-id")

    enrichment = queryset.first()
    return _to_player_record(enrichment) if enrichment else None


def get_latest_player_enrichment(
    player_id: int,
    *,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    club_id: int | None = None,
) -> PlayerSeasonEnrichmentRecord | None:
    return get_player_season_enrichment(
        player_id,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
        club_id=club_id,
    )


def get_club_season_enrichment(
    club_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
) -> ClubSeasonEnrichmentRecord | None:
    queryset = _apply_club_filters(
        _club_queryset(),
        club_id=club_id,
        provider=provider,
        season_label=season_label,
        season=season,
        competition_code=competition_code,
        competition_name=competition_name,
    ).order_by("-season_label", "-last_synced_at", "-updated_at", "-id")

    enrichment = queryset.first()
    return _to_club_record(enrichment) if enrichment else None


def get_latest_club_enrichment(
    club_id: int,
    *,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
) -> ClubSeasonEnrichmentRecord | None:
    return get_club_season_enrichment(
        club_id,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
    )


def get_player_summary_context(
    player_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    club_id: int | None = None,
) -> PlayerSeasonEnrichmentRecord | None:
    return get_player_season_enrichment(
        player_id=player_id,
        season_label=season_label,
        season=season,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
        club_id=club_id,
    )


def get_player_season_data(
    player_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    club_id: int | None = None,
) -> PlayerSeasonEnrichmentRecord | None:
    return get_player_summary_context(
        player_id=player_id,
        season_label=season_label,
        season=season,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
        club_id=club_id,
    )


def get_club_summary_context(
    club_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
) -> ClubSeasonEnrichmentRecord | None:
    return get_club_season_enrichment(
        club_id=club_id,
        season_label=season_label,
        season=season,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
    )


def get_club_season_data(
    club_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
) -> ClubSeasonEnrichmentRecord | None:
    return get_club_summary_context(
        club_id=club_id,
        season_label=season_label,
        season=season,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
    )


def list_enriched_players(
    *,
    player_id: int | None = None,
    club_id: int | None = None,
    provider: str | None = None,
    season_label: str | None = None,
    season: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    position: str | None = None,
    search: str | None = None,
    min_minutes: int | None = None,
    min_goals: int | None = None,
    min_assists: int | None = None,
    min_xg: Decimal | float | str | None = None,
    min_xa: Decimal | float | str | None = None,
    order_by: str = "last_synced_at",
    ordering: str | None = None,
    descending: bool = True,
    include_unavailable: bool | None = None,
    limit: int | None = None,
) -> list[PlayerSeasonEnrichmentRecord]:
    del include_unavailable

    resolved_order_by = _normalise_order_by(
        order_by=order_by,
        ordering=ordering,
        default="last_synced_at",
    )

    queryset = _apply_player_filters(
        _player_queryset(),
        player_id=player_id,
        club_id=club_id,
        provider=provider,
        season_label=season_label,
        season=season,
        competition_code=competition_code,
        competition_name=competition_name,
        position=position,
        search=search,
        min_minutes=min_minutes,
        min_goals=min_goals,
        min_assists=min_assists,
        min_xg=min_xg,
        min_xa=min_xa,
    ).order_by(
        *resolve_ordering(
            allowed_fields=PLAYER_ORDERING_FIELDS,
            order_by=resolved_order_by,
            descending=descending,
        )
    )

    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        queryset = queryset[:limit]

    return [_to_player_record(enrichment) for enrichment in queryset]


def get_enriched_players(
    *,
    player_id: int | None = None,
    club_id: int | None = None,
    provider: str | None = None,
    season_label: str | None = None,
    season: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    position: str | None = None,
    search: str | None = None,
    min_minutes: int | None = None,
    min_goals: int | None = None,
    min_assists: int | None = None,
    min_xg: Decimal | float | str | None = None,
    min_xa: Decimal | float | str | None = None,
    order_by: str = "last_synced_at",
    ordering: str | None = None,
    descending: bool = True,
    include_unavailable: bool | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    results = list_enriched_players(
        player_id=player_id,
        club_id=club_id,
        provider=provider,
        season_label=season_label,
        season=season,
        competition_code=competition_code,
        competition_name=competition_name,
        position=position,
        search=search,
        min_minutes=min_minutes,
        min_goals=min_goals,
        min_assists=min_assists,
        min_xg=min_xg,
        min_xa=min_xa,
        order_by=order_by,
        ordering=ordering,
        descending=descending,
        include_unavailable=include_unavailable,
        limit=limit,
    )
    return {
        "count": len(results),
        "results": results,
    }


def list_enriched_club_players(
    club_id: int,
    *,
    provider: str | None = None,
    season_label: str | None = None,
    season: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    position: str | None = None,
    search: str | None = None,
    min_minutes: int | None = None,
    min_goals: int | None = None,
    min_assists: int | None = None,
    min_xg: Decimal | float | str | None = None,
    min_xa: Decimal | float | str | None = None,
    order_by: str = "last_synced_at",
    ordering: str | None = None,
    descending: bool = True,
    include_unavailable: bool | None = None,
    limit: int | None = None,
) -> list[PlayerSeasonEnrichmentRecord]:
    return list_enriched_players(
        club_id=club_id,
        provider=provider,
        season_label=season_label,
        season=season,
        competition_code=competition_code,
        competition_name=competition_name,
        position=position,
        search=search,
        min_minutes=min_minutes,
        min_goals=min_goals,
        min_assists=min_assists,
        min_xg=min_xg,
        min_xa=min_xa,
        order_by=order_by,
        ordering=ordering,
        descending=descending,
        include_unavailable=include_unavailable,
        limit=limit,
    )


def list_enriched_clubs(
    *,
    club_id: int | None = None,
    provider: str | None = None,
    season_label: str | None = None,
    season: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    order_by: str = "last_synced_at",
    ordering: str | None = None,
    descending: bool = True,
    limit: int | None = None,
) -> list[ClubSeasonEnrichmentRecord]:
    resolved_order_by = _normalise_order_by(
        order_by=order_by,
        ordering=ordering,
        default="last_synced_at",
    )

    queryset = _apply_club_filters(
        _club_queryset(),
        club_id=club_id,
        provider=provider,
        season_label=season_label,
        season=season,
        competition_code=competition_code,
        competition_name=competition_name,
    ).order_by(
        *resolve_ordering(
            allowed_fields=CLUB_ORDERING_FIELDS,
            order_by=resolved_order_by,
            descending=descending,
        )
    )

    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        queryset = queryset[:limit]

    return [_to_club_record(enrichment) for enrichment in queryset]