from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from services.playerdata.helpers import latest_datetime
from services.playerdata.queries import (
    ClubSeasonEnrichmentRecord,
    PlayerSeasonEnrichmentRecord,
    get_club_season_enrichment,
    get_player_season_enrichment,
)


def format_number(value: Decimal | int | float | None, *, decimal_places: int = 1) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, Decimal):
        return f"{value:.{decimal_places}f}"
    if isinstance(value, float):
        return f"{value:.{decimal_places}f}"
    return f"{value:,}"


def competition_label(competition_name: str | None, competition_code: str | None) -> str:
    if competition_name:
        return competition_name
    if competition_code:
        return competition_code
    return "this competition"


def metric_difference(
    left_value: Decimal | int,
    right_value: Decimal | int,
) -> Decimal | int:
    return left_value - right_value


def winner_for_metric(
    *,
    left_name: str,
    right_name: str,
    left_value: Decimal | int | None,
    right_value: Decimal | int | None,
    direction: str,
) -> tuple[str | None, bool, bool, Decimal | int | None]:
    if left_value is None or right_value is None:
        return None, False, False, None

    if left_value == right_value:
        return None, True, True, metric_difference(left_value, right_value)

    if direction == "higher":
        return (
            left_name if left_value > right_value else right_name,
            False,
            True,
            metric_difference(left_value, right_value),
        )

    if direction == "lower":
        return (
            left_name if left_value < right_value else right_name,
            False,
            True,
            metric_difference(left_value, right_value),
        )

    raise ValueError(f"Unsupported comparison direction: {direction}")


@dataclass(frozen=True)
class MetricComparison:
    key: str
    label: str
    unit: str
    direction: str
    left_value: Decimal | int | None
    right_value: Decimal | int | None
    winner: str | None
    is_tie: bool
    is_comparable: bool
    difference: Decimal | int | None
    sentence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "player_a_value": self.player_a_value,
            "player_a_formatted": self.player_a_formatted,
            "player_b_value": self.player_b_value,
            "player_b_formatted": self.player_b_formatted,
            "delta": self.delta,
            "formatted_delta": self.formatted_delta,
            "unit": self.unit or None,
            "winner": self.winner,
            "is_tie": self.is_tie,
        }

    @property
    def metric_key(self) -> str:
        return self.key

    @property
    def player_a_value(self) -> float | int | None:
        if isinstance(self.left_value, Decimal):
            return float(self.left_value)
        return self.left_value

    @property
    def player_a_formatted(self) -> str | None:
        if self.left_value is None:
            return None
        return format_number(self.left_value)

    @property
    def player_b_value(self) -> float | int | None:
        if isinstance(self.right_value, Decimal):
            return float(self.right_value)
        return self.right_value

    @property
    def player_b_formatted(self) -> str | None:
        if self.right_value is None:
            return None
        return format_number(self.right_value)

    @property
    def delta(self) -> float | int | None:
        if isinstance(self.difference, Decimal):
            return float(self.difference)
        return self.difference

    @property
    def formatted_delta(self) -> str | None:
        if self.difference is None:
            return None
        return format_number(self.difference)


@dataclass(frozen=True)
class ComparisonContext:
    provider: str | None
    season_label: str | None
    competition_code: str | None
    competition_name: str | None
    same_provider: bool
    same_season: bool
    same_competition: bool
    left_last_synced_at: datetime | None
    right_last_synced_at: datetime | None
    sentence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "season": self.season,
            "competition_code": self.competition_code,
            "competition_name": self.competition_name,
            "same_provider": self.same_provider,
            "same_season": self.same_season,
            "same_competition": self.same_competition,
            "left_last_synced_at": self.left_last_synced_at,
            "right_last_synced_at": self.right_last_synced_at,
            "sentence": self.sentence,
        }

    @property
    def season(self) -> str | None:
        return self.season_label


@dataclass(frozen=True)
class PlayerComparisonSide:
    player_id: int
    player_name: str
    club_id: int | None
    club_name: str | None
    provider: str
    season_label: str
    competition_code: str
    competition_name: str
    primary_position: str
    secondary_positions: list[str]
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


@dataclass(frozen=True)
class ClubComparisonSide:
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


@dataclass(frozen=True)
class PlayerSeasonComparison:
    left: PlayerComparisonSide
    right: PlayerComparisonSide
    context: ComparisonContext
    metrics: list[MetricComparison]
    summary_lines: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "player_a": self.player_a.to_dict(),
            "player_b": self.player_b.to_dict(),
            "context": self.context.to_dict(),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "summary_lines": self.summary_lines,
            "overall_winner": self.overall_winner,
            "explanation": self.explanation,
            "provider_coverage": self.provider_coverage,
            "has_comparison_data": self.has_comparison_data,
            "missing_reasons": self.missing_reasons,
        }

    @property
    def player_a(self) -> PlayerComparisonSide:
        return self.left

    @property
    def player_b(self) -> PlayerComparisonSide:
        return self.right

    @property
    def overall_winner(self) -> dict[str, Any]:
        comparable_metrics = [metric for metric in self.metrics if metric.is_comparable]
        left_wins = sum(1 for metric in comparable_metrics if metric.winner == self.left.player_name)
        right_wins = sum(1 for metric in comparable_metrics if metric.winner == self.right.player_name)
        tied_count = sum(1 for metric in comparable_metrics if metric.is_tie)

        if left_wins == 0 and right_wins == 0 and tied_count == 0:
            return {
                "winner": None,
                "winner_player_id": None,
                "reason": "No metrics could be compared honestly.",
            }

        if left_wins == right_wins:
            return {
                "winner": "tie",
                "winner_player_id": None,
                "reason": (
                    f"Both players lead the same number of comparable metrics "
                    f"({left_wins} each)."
                ),
            }

        if left_wins > right_wins:
            return {
                "winner": self.left.player_name,
                "winner_player_id": self.left.player_id,
                "reason": (
                    f"{self.left.player_name} leads {left_wins} comparable metrics "
                    f"to {right_wins}."
                ),
            }

        return {
            "winner": self.right.player_name,
            "winner_player_id": self.right.player_id,
            "reason": (
                f"{self.right.player_name} leads {right_wins} comparable metrics "
                f"to {left_wins}."
            ),
        }

    @property
    def explanation(self) -> dict[str, Any]:
        comparable_metrics = [metric for metric in self.metrics if metric.is_comparable]
        tied_metrics = [metric.label for metric in comparable_metrics if metric.is_tie]
        missing_metrics = [metric.label for metric in self.metrics if not metric.is_comparable]

        strengths: list[str] = []
        watchouts: list[str] = []
        notes: list[str] = [self.context.sentence]

        winner_block = self.overall_winner
        if winner_block["winner"] and winner_block["winner"] != "tie":
            strengths.append(winner_block["reason"])
        elif winner_block["winner"] == "tie":
            notes.append(winner_block["reason"])
        else:
            watchouts.append(winner_block["reason"])

        if tied_metrics:
            notes.append(f"Tied metrics: {', '.join(tied_metrics)}.")
        if missing_metrics:
            watchouts.append(
                f"Metrics not compared because of missing values: {', '.join(missing_metrics)}."
            )

        return {
            "headline": "Deterministic player comparison",
            "summary": self.summary_lines[1] if len(self.summary_lines) > 1 else self.context.sentence,
            "strengths": strengths,
            "watchouts": watchouts,
            "notes": notes,
        }

    @property
    def provider_coverage(self) -> dict[str, Any]:
        coverage_notes = [self.context.sentence]

        if self.left.last_synced_at is not None:
            coverage_notes.append(
                f"{self.left.player_name} last synced at {self.left.last_synced_at.isoformat()}."
            )
        else:
            coverage_notes.append(f"{self.left.player_name} has no stored sync timestamp.")

        if self.right.last_synced_at is not None:
            coverage_notes.append(
                f"{self.right.player_name} last synced at {self.right.last_synced_at.isoformat()}."
            )
        else:
            coverage_notes.append(f"{self.right.player_name} has no stored sync timestamp.")

        if self.context.same_provider:
            provider_value = self.context.provider
        else:
            provider_value = "mixed"

        latest_synced_at_value = latest_datetime(
            self.left.last_synced_at,
            self.right.last_synced_at,
        )

        if self.left.last_synced_at is not None and self.right.last_synced_at is not None:
            coverage_status = "available"
            freshness_label = "synced"
        elif latest_synced_at_value is not None:
            coverage_status = "available"
            freshness_label = "partial"
        else:
            coverage_status = "unknown"
            freshness_label = "unknown"

        return {
            "provider": provider_value,
            "has_data": True,
            "coverage_status": coverage_status,
            "freshness_label": freshness_label,
            "source_updated_at": None,
            "last_synced_at": latest_synced_at_value,
            "matches_sampled": None,
            "minutes_sampled": None,
            "coverage_notes": coverage_notes,
        }

    @property
    def has_comparison_data(self) -> bool:
        return True

    @property
    def missing_reasons(self) -> list[str]:
        return []


@dataclass(frozen=True)
class ClubSeasonComparison:
    left: ClubComparisonSide
    right: ClubComparisonSide
    context: ComparisonContext
    metrics: list[MetricComparison]
    summary_lines: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "context": self.context.to_dict(),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "summary_lines": self.summary_lines,
        }


PLAYER_METRICS: tuple[dict[str, str], ...] = (
    {"key": "goals", "label": "Goals", "unit": "", "direction": "higher"},
    {"key": "assists", "label": "Assists", "unit": "", "direction": "higher"},
    {"key": "xg", "label": "xG", "unit": "", "direction": "higher"},
    {"key": "xa", "label": "xA", "unit": "", "direction": "higher"},
    {"key": "shots", "label": "Shots", "unit": "", "direction": "higher"},
    {"key": "key_passes", "label": "Key passes", "unit": "", "direction": "higher"},
    {"key": "minutes_played", "label": "Minutes", "unit": "", "direction": "higher"},
    {"key": "matches_played", "label": "Matches", "unit": "", "direction": "higher"},
)

CLUB_METRICS: tuple[dict[str, str], ...] = (
    {"key": "wins", "label": "Wins", "unit": "", "direction": "higher"},
    {"key": "draws", "label": "Draws", "unit": "", "direction": "higher"},
    {"key": "losses", "label": "Losses", "unit": "", "direction": "lower"},
    {"key": "goals_for", "label": "Goals scored", "unit": "", "direction": "higher"},
    {"key": "goals_against", "label": "Goals conceded", "unit": "", "direction": "lower"},
    {"key": "xg", "label": "xG", "unit": "", "direction": "higher"},
    {"key": "xga", "label": "xGA", "unit": "", "direction": "lower"},
    {"key": "npxg", "label": "npxG", "unit": "", "direction": "higher"},
    {"key": "ppda", "label": "PPDA", "unit": "", "direction": "lower"},
    {"key": "matches_played", "label": "Matches", "unit": "", "direction": "higher"},
)


def _context_sentence(
    *,
    left_provider: str,
    right_provider: str,
    left_season_label: str,
    right_season_label: str,
    left_competition_code: str,
    right_competition_code: str,
    left_competition_name: str,
    right_competition_name: str,
) -> str:
    same_provider = left_provider == right_provider
    same_season = left_season_label == right_season_label
    same_competition = (
        (left_competition_code or "") == (right_competition_code or "")
        and (left_competition_name or "") == (right_competition_name or "")
    )

    if same_provider and same_season and same_competition:
        return (
            f"Both records come from {left_provider} in the {left_season_label} season "
            f"for {competition_label(left_competition_name, left_competition_code)}."
        )

    return (
        f"Left record: {left_provider}, {left_season_label}, "
        f"{competition_label(left_competition_name, left_competition_code)}. "
        f"Right record: {right_provider}, {right_season_label}, "
        f"{competition_label(right_competition_name, right_competition_code)}."
    )


def _build_context(
    *,
    left_provider: str,
    right_provider: str,
    left_season_label: str,
    right_season_label: str,
    left_competition_code: str,
    right_competition_code: str,
    left_competition_name: str,
    right_competition_name: str,
    left_last_synced_at: datetime | None,
    right_last_synced_at: datetime | None,
) -> ComparisonContext:
    same_provider = left_provider == right_provider
    same_season = left_season_label == right_season_label
    same_competition = (
        (left_competition_code or "") == (right_competition_code or "")
        and (left_competition_name or "") == (right_competition_name or "")
    )

    provider = left_provider if same_provider else None
    season_label = left_season_label if same_season else None
    competition_code = left_competition_code if same_competition else None
    competition_name = left_competition_name if same_competition else None

    return ComparisonContext(
        provider=provider,
        season_label=season_label,
        competition_code=competition_code,
        competition_name=competition_name,
        same_provider=same_provider,
        same_season=same_season,
        same_competition=same_competition,
        left_last_synced_at=left_last_synced_at,
        right_last_synced_at=right_last_synced_at,
        sentence=_context_sentence(
            left_provider=left_provider,
            right_provider=right_provider,
            left_season_label=left_season_label,
            right_season_label=right_season_label,
            left_competition_code=left_competition_code,
            right_competition_code=right_competition_code,
            left_competition_name=left_competition_name,
            right_competition_name=right_competition_name,
        ),
    )


def _metric_sentence(
    *,
    label: str,
    left_name: str,
    right_name: str,
    left_value: Decimal | int | None,
    right_value: Decimal | int | None,
    winner: str | None,
    is_tie: bool,
    is_comparable: bool,
) -> str:
    if not is_comparable:
        return (
            f"{label} could not be compared honestly because at least one record is missing a value."
        )

    if is_tie:
        return (
            f"{label} is level: {left_name} {format_number(left_value)} and "
            f"{right_name} {format_number(right_value)}."
        )

    return (
        f"{winner} leads {label.lower()}: {left_name} {format_number(left_value)} vs "
        f"{right_name} {format_number(right_value)}."
    )


def _compare_metric(
    *,
    key: str,
    label: str,
    unit: str,
    direction: str,
    left_name: str,
    right_name: str,
    left_value: Decimal | int | None,
    right_value: Decimal | int | None,
) -> MetricComparison:
    winner, is_tie, is_comparable, difference = winner_for_metric(
        left_name=left_name,
        right_name=right_name,
        left_value=left_value,
        right_value=right_value,
        direction=direction,
    )

    return MetricComparison(
        key=key,
        label=label,
        unit=unit,
        direction=direction,
        left_value=left_value,
        right_value=right_value,
        winner=winner,
        is_tie=is_tie,
        is_comparable=is_comparable,
        difference=difference,
        sentence=_metric_sentence(
            label=label,
            left_name=left_name,
            right_name=right_name,
            left_value=left_value,
            right_value=right_value,
            winner=winner,
            is_tie=is_tie,
            is_comparable=is_comparable,
        ),
    )


def _player_side(record: PlayerSeasonEnrichmentRecord) -> PlayerComparisonSide:
    return PlayerComparisonSide(
        player_id=record.player_id,
        player_name=record.player_name,
        club_id=record.club_id,
        club_name=record.club_name,
        provider=record.provider,
        season_label=record.season_label,
        competition_code=record.competition_code,
        competition_name=record.competition_name,
        primary_position=record.primary_position,
        secondary_positions=record.secondary_positions,
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
        last_synced_at=record.last_synced_at,
        updated_at=record.updated_at,
    )


def _club_side(record: ClubSeasonEnrichmentRecord) -> ClubComparisonSide:
    return ClubComparisonSide(
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
        last_synced_at=record.last_synced_at,
        updated_at=record.updated_at,
    )


def _player_metrics(
    left: PlayerSeasonEnrichmentRecord,
    right: PlayerSeasonEnrichmentRecord,
) -> list[MetricComparison]:
    comparisons: list[MetricComparison] = []

    for spec in PLAYER_METRICS:
        comparisons.append(
            _compare_metric(
                key=spec["key"],
                label=spec["label"],
                unit=spec["unit"],
                direction=spec["direction"],
                left_name=left.player_name,
                right_name=right.player_name,
                left_value=getattr(left, spec["key"]),
                right_value=getattr(right, spec["key"]),
            )
        )

    return comparisons


def _club_metrics(
    left: ClubSeasonEnrichmentRecord,
    right: ClubSeasonEnrichmentRecord,
) -> list[MetricComparison]:
    comparisons: list[MetricComparison] = []

    for spec in CLUB_METRICS:
        comparisons.append(
            _compare_metric(
                key=spec["key"],
                label=spec["label"],
                unit=spec["unit"],
                direction=spec["direction"],
                left_name=left.club_name,
                right_name=right.club_name,
                left_value=getattr(left, spec["key"]),
                right_value=getattr(right, spec["key"]),
            )
        )

    return comparisons


def build_player_comparison_summary(
    comparison: PlayerSeasonComparison,
) -> list[str]:
    lines = [
        comparison.context.sentence,
        (
            f"{comparison.left.player_name} played {comparison.left.minutes_played:,} minutes "
            f"across {comparison.left.matches_played:,} matches, while "
            f"{comparison.right.player_name} played {comparison.right.minutes_played:,} minutes "
            f"across {comparison.right.matches_played:,} matches."
        ),
    ]

    comparable_metrics = [metric for metric in comparison.metrics if metric.is_comparable]
    lead_metrics = [metric for metric in comparable_metrics if metric.winner]
    tied_metrics = [metric for metric in comparable_metrics if metric.is_tie]
    missing_metrics = [metric for metric in comparison.metrics if not metric.is_comparable]

    if lead_metrics:
        left_leads = [
            metric.label for metric in lead_metrics if metric.winner == comparison.left.player_name
        ]
        right_leads = [
            metric.label for metric in lead_metrics if metric.winner == comparison.right.player_name
        ]

        if left_leads:
            lines.append(f"{comparison.left.player_name} leads in: {', '.join(left_leads)}.")
        if right_leads:
            lines.append(f"{comparison.right.player_name} leads in: {', '.join(right_leads)}.")

    if tied_metrics:
        lines.append(f"Tied metrics: {', '.join(metric.label for metric in tied_metrics)}.")

    if missing_metrics:
        lines.append(
            "Metrics not compared because of missing values: "
            f"{', '.join(metric.label for metric in missing_metrics)}."
        )

    return lines


def build_club_comparison_summary(
    comparison: ClubSeasonComparison,
) -> list[str]:
    lines = [
        comparison.context.sentence,
        (
            f"{comparison.left.club_name} played {comparison.left.matches_played:,} matches, "
            f"while {comparison.right.club_name} played {comparison.right.matches_played:,} matches."
        ),
    ]

    comparable_metrics = [metric for metric in comparison.metrics if metric.is_comparable]
    lead_metrics = [metric for metric in comparable_metrics if metric.winner]
    tied_metrics = [metric for metric in comparable_metrics if metric.is_tie]
    missing_metrics = [metric for metric in comparison.metrics if not metric.is_comparable]

    if lead_metrics:
        left_leads = [
            metric.label for metric in lead_metrics if metric.winner == comparison.left.club_name
        ]
        right_leads = [
            metric.label for metric in lead_metrics if metric.winner == comparison.right.club_name
        ]

        if left_leads:
            lines.append(f"{comparison.left.club_name} leads in: {', '.join(left_leads)}.")
        if right_leads:
            lines.append(f"{comparison.right.club_name} leads in: {', '.join(right_leads)}.")

    if tied_metrics:
        lines.append(f"Tied metrics: {', '.join(metric.label for metric in tied_metrics)}.")

    if missing_metrics:
        lines.append(
            "Metrics not compared because of missing values: "
            f"{', '.join(metric.label for metric in missing_metrics)}."
        )

    return lines


def build_comparison_table_data(
    comparison: PlayerSeasonComparison | ClubSeasonComparison,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for metric in comparison.metrics:
        payload = metric.to_dict()

        # Keep legacy aliases for existing API/tests while preserving new schema.
        payload.setdefault("metric_key", payload.get("key"))
        payload.setdefault("left_value", payload.get("player_a_value"))
        payload.setdefault("right_value", payload.get("player_b_value"))
        payload.setdefault("sentence", metric.sentence)

        rows.append(payload)

    return rows


def build_player_comparison(
    player_a_id: int,
    player_b_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    club_a_id: int | None = None,
    club_b_id: int | None = None,
) -> PlayerSeasonComparison | None:
    resolved_season_label = season_label or season

    left_record = get_player_season_enrichment(
        player_a_id,
        season_label=resolved_season_label,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
        club_id=club_a_id,
    )
    right_record = get_player_season_enrichment(
        player_b_id,
        season_label=resolved_season_label,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
        club_id=club_b_id,
    )

    if left_record is None or right_record is None:
        return None

    left = _player_side(left_record)
    right = _player_side(right_record)

    context = _build_context(
        left_provider=left.provider,
        right_provider=right.provider,
        left_season_label=left.season_label,
        right_season_label=right.season_label,
        left_competition_code=left.competition_code,
        right_competition_code=right.competition_code,
        left_competition_name=left.competition_name,
        right_competition_name=right.competition_name,
        left_last_synced_at=left.last_synced_at,
        right_last_synced_at=right.last_synced_at,
    )

    metrics = _player_metrics(left_record, right_record)
    comparison = PlayerSeasonComparison(
        left=left,
        right=right,
        context=context,
        metrics=metrics,
        summary_lines=[],
    )

    return PlayerSeasonComparison(
        left=comparison.left,
        right=comparison.right,
        context=comparison.context,
        metrics=comparison.metrics,
        summary_lines=build_player_comparison_summary(comparison),
    )

compare_player_seasons = build_player_comparison
compare_players = build_player_comparison
get_player_comparison = build_player_comparison


def compare_club_seasons(
    club_a_id: int,
    club_b_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
) -> ClubSeasonComparison | None:
    resolved_season_label = season_label or season

    left_record = get_club_season_enrichment(
        club_a_id,
        season_label=resolved_season_label,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
    )
    right_record = get_club_season_enrichment(
        club_b_id,
        season_label=resolved_season_label,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
    )

    if left_record is None or right_record is None:
        return None

    left = _club_side(left_record)
    right = _club_side(right_record)

    context = _build_context(
        left_provider=left.provider,
        right_provider=right.provider,
        left_season_label=left.season_label,
        right_season_label=right.season_label,
        left_competition_code=left.competition_code,
        right_competition_code=right.competition_code,
        left_competition_name=left.competition_name,
        right_competition_name=right.competition_name,
        left_last_synced_at=left.last_synced_at,
        right_last_synced_at=right.last_synced_at,
    )

    metrics = _club_metrics(left_record, right_record)
    comparison = ClubSeasonComparison(
        left=left,
        right=right,
        context=context,
        metrics=metrics,
        summary_lines=[],
    )

    return ClubSeasonComparison(
        left=comparison.left,
        right=comparison.right,
        context=comparison.context,
        metrics=comparison.metrics,
        summary_lines=build_club_comparison_summary(comparison),
    )