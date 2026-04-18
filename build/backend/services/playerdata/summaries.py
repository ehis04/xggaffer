from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from services.playerdata.queries import (
    ClubSeasonEnrichmentRecord,
    PlayerSeasonEnrichmentRecord,
    get_club_season_enrichment,
    get_player_season_enrichment,
    list_enriched_clubs,
    list_enriched_players,
)


def format_int(value: int | None) -> str:
    if value is None:
        return "0"
    return f"{value:,}"


def format_decimal(value: Decimal | None, places: int = 1) -> str | None:
    if value is None:
        return None
    return f"{value:.{places}f}"


def format_datetime_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M UTC")


def competition_label(competition_name: str, competition_code: str) -> str:
    return competition_name or competition_code or "this competition"


def latest_datetime(*values: datetime | None) -> datetime | None:
    present_values = [value for value in values if value is not None]
    return max(present_values) if present_values else None


def _build_metric(
    *,
    key: str,
    label: str,
    value: int | float | Decimal | None,
    unit: str | None = None,
) -> dict[str, Any]:
    if isinstance(value, Decimal):
        serialisable_value: int | float | None = float(value)
        formatted_value = format_decimal(value)
    else:
        serialisable_value = value
        formatted_value = None if value is None else str(value)

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


def _build_provider_coverage_block(
    *,
    provider: str,
    last_synced_at: datetime | None,
    updated_at: datetime | None,
    matches_sampled: int | None,
    minutes_sampled: int | None,
) -> dict[str, Any]:
    coverage_notes: list[str] = []

    if last_synced_at is not None:
        coverage_status = "available"
        freshness_label = "synced"
    elif updated_at is not None:
        coverage_status = "available"
        freshness_label = "stored"
        coverage_notes.append("No explicit sync timestamp is stored; using updated_at instead.")
    else:
        coverage_status = "unknown"
        freshness_label = "unknown"
        coverage_notes.append("No sync or updated timestamp is stored.")

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


def _build_freshness_sentence(
    *,
    provider: str,
    season_label: str,
    competition_code: str,
    competition_name: str,
    last_synced_at: datetime | None,
    updated_at: datetime | None,
) -> str:
    competition_name_label = competition_label(competition_name, competition_code)

    if last_synced_at is not None:
        return (
            f"{provider} data is available for the {season_label} season in "
            f"{competition_name_label} and was last synced on {format_datetime_utc(last_synced_at)}."
        )

    return (
        f"{provider} data is available for the {season_label} season in "
        f"{competition_name_label}, but no sync timestamp is stored."
    )


@dataclass(frozen=True)
class DataFreshnessSummary:
    provider: str
    season_label: str
    competition_code: str
    competition_name: str
    last_synced_at: datetime | None
    updated_at: datetime | None
    is_available: bool
    sentence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderCoverageItem:
    provider: str
    season_label: str
    competition_code: str
    competition_name: str
    club_id: int | None
    club_name: str | None
    last_synced_at: datetime | None
    updated_at: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderCoverageSummary:
    entity_type: str
    entity_id: int
    entity_name: str
    record_count: int
    providers: list[str]
    seasons: list[str]
    competitions: list[str]
    latest_synced_at: datetime | None
    latest_updated_at: datetime | None
    items: list[ProviderCoverageItem]
    sentences: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True)
class PlayerSeasonSummary:
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
    freshness: DataFreshnessSummary
    sentences: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "freshness": self.freshness.to_dict(),
        }

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
    def explanation(self) -> dict[str, Any]:
        strengths: list[str] = []
        watchouts: list[str] = []
        notes: list[str] = []

        if self.goals > 0:
            strengths.append(f"Recorded {format_int(self.goals)} goal{'s' if self.goals != 1 else ''}.")
        if self.assists > 0:
            strengths.append(
                f"Recorded {format_int(self.assists)} assist{'s' if self.assists != 1 else ''}."
            )
        if self.minutes_played < 300:
            watchouts.append("Sample size is small based on minutes played.")
        if self.xg is not None:
            notes.append(f"xG value stored for this season: {format_decimal(self.xg)}.")
        if self.xa is not None:
            notes.append(f"xA value stored for this season: {format_decimal(self.xa)}.")
        notes.append(self.freshness.sentence)

        return {
            "headline": "Deterministic season summary",
            "summary": self.sentences[0] if self.sentences else None,
            "strengths": strengths,
            "watchouts": watchouts,
            "notes": notes,
        }

    @property
    def provider_coverage(self) -> dict[str, Any]:
        return _build_provider_coverage_block(
            provider=self.provider,
            last_synced_at=self.freshness.last_synced_at,
            updated_at=self.freshness.updated_at,
            matches_sampled=self.matches_played,
            minutes_sampled=self.minutes_played,
        )

    @property
    def has_summary_data(self) -> bool:
        return True

    @property
    def missing_reasons(self) -> list[str]:
        return []


@dataclass(frozen=True)
class ClubSeasonSummary:
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
    freshness: DataFreshnessSummary
    sentences: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "freshness": self.freshness.to_dict(),
        }

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
        strengths: list[str] = []
        watchouts: list[str] = []
        notes: list[str] = []

        if self.wins > self.losses:
            strengths.append("Wins exceed losses in the stored season summary.")
        if self.goals_for > self.goals_against:
            strengths.append("Goals scored exceed goals conceded.")
        if self.losses > self.wins:
            watchouts.append("Losses exceed wins in the stored season summary.")
        if self.xg is not None:
            notes.append(f"xG value stored for this season: {format_decimal(self.xg)}.")
        if self.xga is not None:
            notes.append(f"xGA value stored for this season: {format_decimal(self.xga)}.")
        notes.append(self.freshness.sentence)

        return {
            "headline": "Deterministic club season summary",
            "summary": self.sentences[0] if self.sentences else None,
            "strengths": strengths,
            "watchouts": watchouts,
            "notes": notes,
        }

    @property
    def provider_coverage(self) -> dict[str, Any]:
        return _build_provider_coverage_block(
            provider=self.provider,
            last_synced_at=self.freshness.last_synced_at,
            updated_at=self.freshness.updated_at,
            matches_sampled=self.matches_played,
            minutes_sampled=None,
        )

    @property
    def has_summary_data(self) -> bool:
        return True

    @property
    def missing_reasons(self) -> list[str]:
        return []


def build_data_freshness_summary(
    *,
    provider: str,
    season_label: str,
    competition_code: str = "",
    competition_name: str = "",
    last_synced_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> DataFreshnessSummary:
    return DataFreshnessSummary(
        provider=provider,
        season_label=season_label,
        competition_code=competition_code,
        competition_name=competition_name,
        last_synced_at=last_synced_at,
        updated_at=updated_at,
        is_available=True,
        sentence=_build_freshness_sentence(
            provider=provider,
            season_label=season_label,
            competition_code=competition_code,
            competition_name=competition_name,
            last_synced_at=last_synced_at,
            updated_at=updated_at,
        ),
    )


def _player_usage_sentence(record: PlayerSeasonEnrichmentRecord) -> str:
    return (
        f"{record.player_name} scored {format_int(record.goals)} goals and produced "
        f"{format_int(record.assists)} assists in {format_int(record.minutes_played)} minutes "
        f"across {format_int(record.matches_played)} matches in the {record.season_label} season."
    )


def _player_chance_creation_sentence(record: PlayerSeasonEnrichmentRecord) -> str:
    parts: list[str] = []

    xg = format_decimal(record.xg)
    xa = format_decimal(record.xa)
    npxg = format_decimal(record.npxg)

    if xg is not None:
        parts.append(f"{xg} xG")
    if xa is not None:
        parts.append(f"{xa} xA")
    if npxg is not None:
        parts.append(f"{npxg} npxG")

    parts.append(f"{format_int(record.shots)} shots")
    parts.append(f"{format_int(record.key_passes)} key passes")

    return f"He recorded {', '.join(parts)}."


def _player_context_sentence(record: PlayerSeasonEnrichmentRecord) -> str:
    competition_name_label = competition_label(record.competition_name, record.competition_code)

    if record.club_name:
        return (
            f"This record is for {record.club_name} in {competition_name_label} "
            f"from the {record.provider} provider."
        )

    return f"This record is in {competition_name_label} from the {record.provider} provider."


def _club_results_sentence(record: ClubSeasonEnrichmentRecord) -> str:
    return (
        f"{record.club_name} played {format_int(record.matches_played)} matches and posted a "
        f"{format_int(record.wins)}-{format_int(record.draws)}-{format_int(record.losses)} "
        f"win-draw-loss record in the {record.season_label} season."
    )


def _club_performance_sentence(record: ClubSeasonEnrichmentRecord) -> str:
    parts = [
        f"{format_int(record.goals_for)} goals scored",
        f"{format_int(record.goals_against)} goals conceded",
    ]

    xg = format_decimal(record.xg)
    xga = format_decimal(record.xga)
    npxg = format_decimal(record.npxg)
    ppda = format_decimal(record.ppda)

    if xg is not None:
        parts.append(f"{xg} xG")
    if xga is not None:
        parts.append(f"{xga} xGA")
    if npxg is not None:
        parts.append(f"{npxg} npxG")
    if ppda is not None:
        parts.append(f"{ppda} PPDA")

    return f"They recorded {', '.join(parts)}."


def _club_context_sentence(record: ClubSeasonEnrichmentRecord) -> str:
    competition_name_label = competition_label(record.competition_name, record.competition_code)
    return f"This record is for {competition_name_label} from the {record.provider} provider."


def build_player_season_summary(
    player_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    club_id: int | None = None,
    enrichment: PlayerSeasonEnrichmentRecord | None = None,
) -> PlayerSeasonSummary | None:
    record = enrichment or get_player_season_enrichment(
        player_id,
        season_label=season_label,
        season=season,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
        club_id=club_id,
    )
    if record is None:
        return None

    freshness = build_data_freshness_summary(
        provider=record.provider,
        season_label=record.season_label,
        competition_code=record.competition_code,
        competition_name=record.competition_name,
        last_synced_at=record.last_synced_at,
        updated_at=record.updated_at,
    )

    sentences = [
        _player_usage_sentence(record),
        _player_chance_creation_sentence(record),
        _player_context_sentence(record),
        freshness.sentence,
    ]

    return PlayerSeasonSummary(
        player_id=record.player_id,
        player_name=record.player_name,
        primary_position=record.primary_position,
        secondary_positions=record.secondary_positions,
        club_id=record.club_id,
        club_name=record.club_name,
        provider=record.provider,
        season_label=record.season_label,
        competition_code=record.competition_code,
        competition_name=record.competition_name,
        matches_played=record.matches_played,
        minutes_played=record.minutes_played,
        goals=record.goals,
        assists=record.assists,
        shots=record.shots,
        xg=record.xg,
        xa=record.xa,
        npg=record.npg,
        npxg=record.npxg,
        key_passes=record.key_passes,
        freshness=freshness,
        sentences=sentences,
    )


get_player_season_summary = build_player_season_summary
build_player_summary_payload = build_player_season_summary
summarise_player_season = build_player_season_summary
summarize_player_season = build_player_season_summary






def build_club_season_summary(
    club_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    enrichment: ClubSeasonEnrichmentRecord | None = None,
) -> ClubSeasonSummary | None:
    record = enrichment or get_club_season_enrichment(
        club_id,
        season_label=season_label,
        season=season,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
    )
    if record is None:
        return None

    freshness = build_data_freshness_summary(
        provider=record.provider,
        season_label=record.season_label,
        competition_code=record.competition_code,
        competition_name=record.competition_name,
        last_synced_at=record.last_synced_at,
        updated_at=record.updated_at,
    )

    sentences = [
        _club_results_sentence(record),
        _club_performance_sentence(record),
        _club_context_sentence(record),
        freshness.sentence,
    ]

    return ClubSeasonSummary(
        club_id=record.club_id,
        club_name=record.club_name,
        provider=record.provider,
        season_label=record.season_label,
        competition_code=record.competition_code,
        competition_name=record.competition_name,
        matches_played=record.matches_played,
        wins=record.wins,
        draws=record.draws,
        losses=record.losses,
        goals_for=record.goals_for,
        goals_against=record.goals_against,
        xg=record.xg,
        xga=record.xga,
        npxg=record.npxg,
        ppda=record.ppda,
        freshness=freshness,
        sentences=sentences,
    )

get_club_season_summary = build_club_season_summary
build_club_summary_payload = build_club_season_summary
summarise_club_season = build_club_season_summary
summarize_club_season = build_club_season_summary

def _build_player_coverage_items(player_id: int) -> list[ProviderCoverageItem]:
    records = list_enriched_players(
        player_id=player_id,
        order_by="season_label",
        descending=True,
    )

    return [
        ProviderCoverageItem(
            provider=record.provider,
            season_label=record.season_label,
            competition_code=record.competition_code,
            competition_name=record.competition_name,
            club_id=record.club_id,
            club_name=record.club_name,
            last_synced_at=record.last_synced_at,
            updated_at=record.updated_at,
        )
        for record in records
    ]


def _build_club_coverage_items(club_id: int) -> list[ProviderCoverageItem]:
    records = list_enriched_clubs(
        club_id=club_id,
        order_by="season_label",
        descending=True,
    )

    return [
        ProviderCoverageItem(
            provider=record.provider,
            season_label=record.season_label,
            competition_code=record.competition_code,
            competition_name=record.competition_name,
            club_id=record.club_id,
            club_name=record.club_name,
            last_synced_at=record.last_synced_at,
            updated_at=record.updated_at,
        )
        for record in records
    ]


def build_player_provider_coverage_summary(player_id: int) -> ProviderCoverageSummary | None:
    records = list_enriched_players(
        player_id=player_id,
        order_by="season_label",
        descending=True,
    )
    if not records:
        return None

    items = _build_player_coverage_items(player_id)
    first_record = records[0]

    providers = sorted({record.provider for record in records})
    seasons = sorted({record.season_label for record in records}, reverse=True)
    competitions = sorted(
        {
            competition_label(record.competition_name, record.competition_code)
            for record in records
        }
    )

    latest_synced_at = latest_datetime(*(record.last_synced_at for record in records))
    latest_updated_at = latest_datetime(*(record.updated_at for record in records))

    sentences = [
        (
            f"{first_record.player_name} has {format_int(len(records))} stored enrichment "
            f"record{'s' if len(records) != 1 else ''} across "
            f"{format_int(len(providers))} provider{'s' if len(providers) != 1 else ''}."
        ),
        (
            f"Available providers: {', '.join(providers)}. "
            f"Available seasons: {', '.join(seasons)}."
        ),
        f"Competitions covered: {', '.join(competitions)}.",
    ]

    if latest_synced_at is not None:
        sentences.append(
            f"The most recent sync timestamp is {format_datetime_utc(latest_synced_at)}."
        )
    elif latest_updated_at is not None:
        sentences.append(
            f"The most recent stored update timestamp is {format_datetime_utc(latest_updated_at)}."
        )

    return ProviderCoverageSummary(
        entity_type="player",
        entity_id=first_record.player_id,
        entity_name=first_record.player_name,
        record_count=len(records),
        providers=providers,
        seasons=seasons,
        competitions=competitions,
        latest_synced_at=latest_synced_at,
        latest_updated_at=latest_updated_at,
        items=items,
        sentences=sentences,
    )


def build_club_provider_coverage_summary(club_id: int) -> ProviderCoverageSummary | None:
    records = list_enriched_clubs(
        club_id=club_id,
        order_by="season_label",
        descending=True,
    )
    if not records:
        return None

    items = _build_club_coverage_items(club_id)
    first_record = records[0]

    providers = sorted({record.provider for record in records})
    seasons = sorted({record.season_label for record in records}, reverse=True)
    competitions = sorted(
        {
            competition_label(record.competition_name, record.competition_code)
            for record in records
        }
    )

    latest_synced_at = latest_datetime(*(record.last_synced_at for record in records))
    latest_updated_at = latest_datetime(*(record.updated_at for record in records))

    sentences = [
        (
            f"{first_record.club_name} has {format_int(len(records))} stored enrichment "
            f"record{'s' if len(records) != 1 else ''} across "
            f"{format_int(len(providers))} provider{'s' if len(providers) != 1 else ''}."
        ),
        (
            f"Available providers: {', '.join(providers)}. "
            f"Available seasons: {', '.join(seasons)}."
        ),
        f"Competitions covered: {', '.join(competitions)}.",
    ]

    if latest_synced_at is not None:
        sentences.append(
            f"The most recent sync timestamp is {format_datetime_utc(latest_synced_at)}."
        )
    elif latest_updated_at is not None:
        sentences.append(
            f"The most recent stored update timestamp is {format_datetime_utc(latest_updated_at)}."
        )

    return ProviderCoverageSummary(
        entity_type="club",
        entity_id=first_record.club_id,
        entity_name=first_record.club_name,
        record_count=len(records),
        providers=providers,
        seasons=seasons,
        competitions=competitions,
        latest_synced_at=latest_synced_at,
        latest_updated_at=latest_updated_at,
        items=items,
        sentences=sentences,
    )