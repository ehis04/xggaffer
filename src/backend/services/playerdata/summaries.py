"""
Summary builders for the playerdata service layer.

Builds readable player and club season summaries, including freshness details, metric payloads, and provider coverage information.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from common.utils import latest_datetime
from services.playerdata.helpers import (
    build_metric_payload,
    build_provider_coverage_payload,
    competition_label,
    format_datetime_utc,
    format_decimal,
    format_int,
)
from services.playerdata.queries import (
    ClubSeasonEnrichmentRecord,
    PlayerSeasonEnrichmentRecord,
    get_club_season_enrichment,
    get_player_season_enrichment,
    list_enriched_clubs,
    list_enriched_players,
)


# ---------------------------------------------------------------------------
# Freshness sentence builder
# ---------------------------------------------------------------------------

# Build a simple sentence describing whether the data is available and when it was last synced
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


# ---------------------------------------------------------------------------
# Summary dataclasses
# ---------------------------------------------------------------------------

# Hold freshness details for one provider and season summary
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

    # Return the freshness summary in dictionary form
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Hold one provider coverage item for a specific record
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

    # Return one provider coverage item in dictionary form
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Hold the full provider coverage summary for one entity
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

    # Return the full provider coverage summary in dictionary form
    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "items": [item.to_dict() for item in self.items],
        }


# Hold one player season summary in typed service form
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

    # Return the full player season summary in dictionary form
    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "freshness": self.freshness.to_dict(),
        }

    # Return the main player details in the structure expected by the API
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

    # Return the linked club details for this player, if available
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

    # Return the provider, season, and competition context for this summary
    @property
    def context(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "season": self.season_label,
            "competition_code": self.competition_code,
            "competition_name": self.competition_name,
        }

    # Return the full list of metric payloads for this player summary
    @property
    def metrics(self) -> list[dict[str, Any]]:
        return [
            build_metric_payload(key="matches_played", label="Matches played", value=self.matches_played),
            build_metric_payload(key="minutes_played", label="Minutes played", value=self.minutes_played),
            build_metric_payload(key="goals", label="Goals", value=self.goals),
            build_metric_payload(key="assists", label="Assists", value=self.assists),
            build_metric_payload(key="shots", label="Shots", value=self.shots),
            build_metric_payload(key="xg", label="xG", value=self.xg),
            build_metric_payload(key="xa", label="xA", value=self.xa),
            build_metric_payload(key="npg", label="Non-penalty goals", value=self.npg),
            build_metric_payload(key="npxg", label="npxG", value=self.npxg),
            build_metric_payload(key="key_passes", label="Key passes", value=self.key_passes),
        ]

    # Return the deterministic explanation block for this player summary
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
        # 300 minutes is the minimum threshold for a meaningful sample size.
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

    # Return provider freshness and coverage details for this summary
    @property
    def provider_coverage(self) -> dict[str, Any]:
        return build_provider_coverage_payload(
            provider=self.provider,
            last_synced_at=self.freshness.last_synced_at,
            updated_at=self.freshness.updated_at,
            matches_sampled=self.matches_played,
            minutes_sampled=self.minutes_played,
        )

    # Show that this summary has data available
    @property
    def has_summary_data(self) -> bool:
        return True

    # Return any missing-data reasons for this summary
    @property
    def missing_reasons(self) -> list[str]:
        return []


# Hold one club season summary in typed service form
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

    # Return the full club season summary in dictionary form
    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "freshness": self.freshness.to_dict(),
        }

    # Return the main club details in the structure expected by the API
    @property
    def club(self) -> dict[str, Any]:
        return {
            "id": self.club_id,
            "name": self.club_name,
            "short_name": self.club_name,
            "crest_url": None,
        }

    # Return the provider, season, and competition context for this summary
    @property
    def context(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "season": self.season_label,
            "competition_code": self.competition_code,
            "competition_name": self.competition_name,
        }

    # Return the full list of metric payloads for this club summary
    @property
    def metrics(self) -> list[dict[str, Any]]:
        return [
            build_metric_payload(key="matches_played", label="Matches played", value=self.matches_played),
            build_metric_payload(key="wins", label="Wins", value=self.wins),
            build_metric_payload(key="draws", label="Draws", value=self.draws),
            build_metric_payload(key="losses", label="Losses", value=self.losses),
            build_metric_payload(key="goals_for", label="Goals for", value=self.goals_for),
            build_metric_payload(key="goals_against", label="Goals against", value=self.goals_against),
            build_metric_payload(key="xg", label="xG", value=self.xg),
            build_metric_payload(key="xga", label="xGA", value=self.xga),
            build_metric_payload(key="npxg", label="npxG", value=self.npxg),
            build_metric_payload(key="ppda", label="PPDA", value=self.ppda),
        ]

    # Return the deterministic explanation block for this club summary
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

    # Return provider freshness and coverage details for this summary
    @property
    def provider_coverage(self) -> dict[str, Any]:
        return build_provider_coverage_payload(
            provider=self.provider,
            last_synced_at=self.freshness.last_synced_at,
            updated_at=self.freshness.updated_at,
            matches_sampled=self.matches_played,
            minutes_sampled=None,
        )

    # Show that this summary has data available
    @property
    def has_summary_data(self) -> bool:
        return True

    # Return any missing-data reasons for this summary
    @property
    def missing_reasons(self) -> list[str]:
        return []


# ---------------------------------------------------------------------------
# Freshness summary factory
# ---------------------------------------------------------------------------

# Build a freshness summary object for one provider and season
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


# ---------------------------------------------------------------------------
# Sentence builders (internal)
# ---------------------------------------------------------------------------

# Build a sentence summarising the player's output and playing time
def _player_usage_sentence(record: PlayerSeasonEnrichmentRecord) -> str:
    return (
        f"{record.player_name} scored {format_int(record.goals)} goals and produced "
        f"{format_int(record.assists)} assists in {format_int(record.minutes_played)} minutes "
        f"across {format_int(record.matches_played)} matches in the {record.season_label} season."
    )


# Build a sentence summarising the player's xG, xA, shots, and key passes
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


# Build a sentence describing the player's club, competition, and provider context
def _player_context_sentence(record: PlayerSeasonEnrichmentRecord) -> str:
    competition_name_label = competition_label(record.competition_name, record.competition_code)

    if record.club_name:
        return (
            f"This record is for {record.club_name} in {competition_name_label} "
            f"from the {record.provider} provider."
        )

    return f"This record is in {competition_name_label} from the {record.provider} provider."


# Build a sentence summarising the club's results for the season
def _club_results_sentence(record: ClubSeasonEnrichmentRecord) -> str:
    return (
        f"{record.club_name} played {format_int(record.matches_played)} matches and posted a "
        f"{format_int(record.wins)}-{format_int(record.draws)}-{format_int(record.losses)} "
        f"win-draw-loss record in the {record.season_label} season."
    )


# Build a sentence summarising the club's goals and advanced metrics
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


# Build a sentence describing the club's competition and provider context
def _club_context_sentence(record: ClubSeasonEnrichmentRecord) -> str:
    competition_name_label = competition_label(record.competition_name, record.competition_code)
    return f"This record is for {competition_name_label} from the {record.provider} provider."


# ---------------------------------------------------------------------------
# Public summary builders
# ---------------------------------------------------------------------------

# Build the full season summary for one player
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


# Aliases for backward compatibility.
get_player_season_summary = build_player_season_summary
build_player_summary_payload = build_player_season_summary
summarise_player_season = build_player_season_summary
summarize_player_season = build_player_season_summary


# Build the full season summary for one club
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


# Aliases for backward compatibility.
get_club_season_summary = build_club_season_summary
build_club_summary_payload = build_club_season_summary
summarise_club_season = build_club_season_summary
summarize_club_season = build_club_season_summary


# ---------------------------------------------------------------------------
# Provider coverage summary builders
# ---------------------------------------------------------------------------

# Build the list of provider coverage items for one player
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


# Build the list of provider coverage items for one club
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


# Build the full provider coverage summary for one player
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


# Build the full provider coverage summary for one club
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
