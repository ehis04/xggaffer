from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

try:
    from data_collection.config.sources import SOURCE_UNDERSTAT, SOURCE_SOFASCORE
except ImportError:
    SOURCE_UNDERSTAT = "understat"
    SOURCE_SOFASCORE = "sofascore"

try:
    from data_collection.core.enums import (
        DATASET_MATCHES,
        DATASET_PLAYERS,
        DATASET_TEAMS,
        DATASET_TEAM_SUMMARIES,
    )
except ImportError:
    DATASET_MATCHES = "matches"
    DATASET_PLAYERS = "players"
    DATASET_TEAMS = "teams"
    DATASET_TEAM_SUMMARIES = "team_summaries"


@dataclass(frozen=True)
class StatOwnershipRule:
    dataset: str
    family: str
    owner: str
    exact_fields: tuple[str, ...] = ()
    field_prefixes: tuple[str, ...] = ()
    notes: str = ""


UNDERSTAT_XG_FIELDS = (
    "xg",
    "home_xg",
    "away_xg",
    "team_xg",
    "opponent_xg",
    "player_xg",
    "shot_xg",
    "npxg",
    "home_npxg",
    "away_npxg",
    "team_npxg",
    "opponent_npxg",
    "player_npxg",
    "xa",
    "player_xa",
    "xpts",
    "x_points",
    "team_xpts",
    "opponent_xpts",
    "shot_x",
    "shot_y",
    "shot_type",
    "shot_result",
    "shot_situation",
    "chance_quality",
    "big_chance",
)

SOFASCORE_CONTROL_FIELDS = (
    "possession",
    "home_possession",
    "away_possession",
    "corners",
    "home_corners",
    "away_corners",
    "fouls",
    "home_fouls",
    "away_fouls",
    "yellow_cards",
    "red_cards",
    "home_yellow_cards",
    "away_yellow_cards",
    "home_red_cards",
    "away_red_cards",
    "saves",
    "home_saves",
    "away_saves",
    "tackles",
    "home_tackles",
    "away_tackles",
    "interceptions",
    "home_interceptions",
    "away_interceptions",
    "clearances",
    "home_clearances",
    "away_clearances",
    "duels",
    "home_duels",
    "away_duels",
    "duels_won",
    "home_duels_won",
    "away_duels_won",
    "aerial_duels",
    "home_aerial_duels",
    "away_aerial_duels",
    "aerial_duels_won",
    "home_aerial_duels_won",
    "away_aerial_duels_won",
    "recoveries",
    "home_recoveries",
    "away_recoveries",
    "blocks",
    "home_blocks",
    "away_blocks",
    "ball_recovery",
    "fouls_committed",
    "fouls_won",
)

SHARED_RESULT_FIELDS = (
    "goals",
    "home_goals",
    "away_goals",
    "score",
    "home_score",
    "away_score",
    "date",
    "league",
    "season",
    "home_team",
    "away_team",
    "match_status",
    "is_finished",
    "minutes",
    "appearances",
    "games",
    "matches",
    "rating",
)

STAT_OWNERSHIP_RULES: tuple[StatOwnershipRule, ...] = (
    StatOwnershipRule(
        dataset=DATASET_MATCHES,
        family="understat_xg_family",
        owner=SOURCE_UNDERSTAT,
        exact_fields=UNDERSTAT_XG_FIELDS,
        field_prefixes=("xg_", "npxg_", "xa_", "xpts_", "shot_"),
        notes="Understat is the primary owner for xG-family, shot context, and attacking chance quality metrics.",
    ),
    StatOwnershipRule(
        dataset=DATASET_PLAYERS,
        family="understat_attacking_quality_family",
        owner=SOURCE_UNDERSTAT,
        exact_fields=(
            "xg",
            "npxg",
            "xa",
            "shots",
            "shots_on_target",
            "shot_x",
            "shot_y",
            "shot_type",
            "shot_situation",
            "chance_quality",
        ),
        field_prefixes=("xg_", "npxg_", "xa_", "shot_"),
        notes="Understat remains the preferred owner for player attacking-quality metrics.",
    ),
    StatOwnershipRule(
        dataset=DATASET_TEAMS,
        family="understat_team_attack_quality_family",
        owner=SOURCE_UNDERSTAT,
        exact_fields=(
            "xg",
            "npxg",
            "xpts",
            "shots",
            "shots_on_target",
            "deep_completions",
            "ppda_att",
            "ppda_def",
        ),
        field_prefixes=("xg_", "npxg_", "xpts_", "shot_"),
        notes="Understat remains the preferred owner for team attack-quality and xG-family metrics.",
    ),
    StatOwnershipRule(
        dataset=DATASET_TEAM_SUMMARIES,
        family="understat_team_summary_family",
        owner=SOURCE_UNDERSTAT,
        exact_fields=(
            "formation",
            "formations_used",
            "game_state",
            "attack_speed",
            "xg_open_play",
            "xg_set_pieces",
            "xg_counter",
            "xg_penalties",
        ),
        field_prefixes=("xg_", "formation_", "game_state_", "attack_"),
        notes="Team summaries remain Understat-owned for now.",
    ),
    StatOwnershipRule(
        dataset=DATASET_MATCHES,
        family="sofascore_control_defensive_family",
        owner=SOURCE_SOFASCORE,
        exact_fields=SOFASCORE_CONTROL_FIELDS,
        field_prefixes=(
            "possession_",
            "corners_",
            "fouls_",
            "cards_",
            "saves_",
            "tackles_",
            "interceptions_",
            "clearances_",
            "duels_",
            "aerial_",
            "recoveries_",
            "blocks_",
        ),
        notes="Sofascore is the primary owner for possession, defensive, and broader control metrics.",
    ),
    StatOwnershipRule(
        dataset=DATASET_PLAYERS,
        family="sofascore_player_defensive_family",
        owner=SOURCE_SOFASCORE,
        exact_fields=(
            "tackles",
            "interceptions",
            "clearances",
            "blocks",
            "recoveries",
            "duels_won",
            "aerial_duels_won",
            "fouls_committed",
            "fouls_won",
            "yellow_cards",
            "red_cards",
            "minutes",
            "rating",
        ),
        field_prefixes=(
            "tackles_",
            "interceptions_",
            "clearances_",
            "blocks_",
            "recoveries_",
            "duels_",
            "aerial_",
            "fouls_",
        ),
        notes="Sofascore is the preferred owner for player defensive contributions and control-style stats.",
    ),
    StatOwnershipRule(
        dataset=DATASET_TEAMS,
        family="sofascore_team_control_family",
        owner=SOURCE_SOFASCORE,
        exact_fields=(
            "possession",
            "corners",
            "fouls",
            "yellow_cards",
            "red_cards",
            "saves",
            "tackles",
            "interceptions",
            "clearances",
            "duels",
            "aerial_duels",
        ),
        field_prefixes=(
            "possession_",
            "corners_",
            "fouls_",
            "cards_",
            "saves_",
            "tackles_",
            "interceptions_",
            "clearances_",
            "duels_",
            "aerial_",
        ),
        notes="Sofascore is the preferred owner for team control and defensive metrics.",
    ),
)

SHARED_FIELD_RULES: dict[str, tuple[str, ...]] = {
    DATASET_MATCHES: SHARED_RESULT_FIELDS,
    DATASET_PLAYERS: (
        "name",
        "team",
        "position",
        "country",
        "minutes",
        "games",
        "rating",
    ),
    DATASET_TEAMS: (
        "team",
        "league",
        "season",
        "matches_played",
        "wins",
        "draws",
        "losses",
        "goals_for",
        "goals_against",
    ),
    DATASET_TEAM_SUMMARIES: (
        "team",
        "league",
        "season",
    ),
}

PROVENANCE_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    DATASET_MATCHES: (
        "source",
        "source_match_id",
        "understat_source_match_id",
        "sofascore_source_match_id",
    ),
    DATASET_PLAYERS: (
        "source",
        "source_player_id",
    ),
    DATASET_TEAMS: (
        "source",
        "source_team_id",
    ),
    DATASET_TEAM_SUMMARIES: (
        "source",
        "source_team_id",
    ),
}


def get_primary_owner(dataset: str, field_name: str) -> str | None:
    dataset_value = _normalise_token(dataset)
    field_value = _normalise_token(field_name)

    if not dataset_value or not field_value:
        return None

    for rule in STAT_OWNERSHIP_RULES:
        if rule.dataset != dataset_value:
            continue

        if field_value in {_normalise_token(field) for field in rule.exact_fields}:
            return rule.owner

        for prefix in rule.field_prefixes:
            if field_value.startswith(_normalise_token(prefix)):
                return rule.owner

    return None


def is_shared_field(dataset: str, field_name: str) -> bool:
    dataset_value = _normalise_token(dataset)
    field_value = _normalise_token(field_name)

    shared_fields = SHARED_FIELD_RULES.get(dataset_value, ())
    return field_value in {_normalise_token(field) for field in shared_fields}


def requires_provenance(dataset: str, field_name: str) -> bool:
    dataset_value = _normalise_token(dataset)
    field_value = _normalise_token(field_name)

    provenance_fields = PROVENANCE_REQUIRED_FIELDS.get(dataset_value, ())
    return field_value in {_normalise_token(field) for field in provenance_fields}


def should_publish_single_owner(dataset: str, field_name: str) -> bool:
    if requires_provenance(dataset, field_name):
        return False

    if is_shared_field(dataset, field_name):
        return False

    return get_primary_owner(dataset, field_name) is not None


def get_publish_owner(dataset: str, field_name: str) -> str | None:
    if not should_publish_single_owner(dataset, field_name):
        return None

    return get_primary_owner(dataset, field_name)


def get_owned_fields_for_source(dataset: str, source: str) -> list[str]:
    dataset_value = _normalise_token(dataset)
    source_value = _normalise_token(source)

    owned_fields: list[str] = []

    for rule in STAT_OWNERSHIP_RULES:
        if rule.dataset != dataset_value or rule.owner != source_value:
            continue

        owned_fields.extend(rule.exact_fields)

    return sorted(set(owned_fields))


def get_rules_for_dataset(dataset: str) -> list[StatOwnershipRule]:
    dataset_value = _normalise_token(dataset)
    return [
        rule
        for rule in STAT_OWNERSHIP_RULES
        if rule.dataset == dataset_value
    ]


def get_ownership_summary() -> dict[str, object]:
    datasets = sorted({rule.dataset for rule in STAT_OWNERSHIP_RULES})

    return {
        "datasets": datasets,
        "primary_owners": {
            dataset: {
                SOURCE_UNDERSTAT: get_owned_fields_for_source(dataset, SOURCE_UNDERSTAT),
                SOURCE_SOFASCORE: get_owned_fields_for_source(dataset, SOURCE_SOFASCORE),
            }
            for dataset in datasets
        },
        "shared_fields": {
            dataset: list(SHARED_FIELD_RULES.get(dataset, ()))
            for dataset in datasets
        },
        "provenance_required_fields": {
            dataset: list(PROVENANCE_REQUIRED_FIELDS.get(dataset, ()))
            for dataset in datasets
        },
    }


def choose_preferred_series(
    df: pd.DataFrame,
    dataset: str,
    canonical_field: str,
    preferred_source_column_map: dict[str, str],
) -> pd.Series:
    owner = get_publish_owner(dataset, canonical_field)

    if owner:
        preferred_column = preferred_source_column_map.get(owner)
        if preferred_column and preferred_column in df.columns:
            return df[preferred_column]

    ordered_candidates = [
        column
        for _, column in preferred_source_column_map.items()
        if column in df.columns
    ]

    if not ordered_candidates:
        return pd.Series(pd.NA, index=df.index, dtype="object")

    if len(ordered_candidates) == 1:
        return df[ordered_candidates[0]]

    combined = df[ordered_candidates].copy()
    combined = combined.replace({"": pd.NA})
    return combined.bfill(axis=1).iloc[:, 0]


def validate_stat_ownership_configuration() -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    for rule in STAT_OWNERSHIP_RULES:
        if rule.owner not in {SOURCE_UNDERSTAT, SOURCE_SOFASCORE}:
            errors.append(
                f"Unsupported owner '{rule.owner}' for dataset '{rule.dataset}' family '{rule.family}'."
            )

        if not rule.exact_fields and not rule.field_prefixes:
            warnings.append(
                f"Rule '{rule.family}' for dataset '{rule.dataset}' has no exact fields or prefixes."
            )

    return {
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total_rules": len(STAT_OWNERSHIP_RULES),
            "datasets": sorted({rule.dataset for rule in STAT_OWNERSHIP_RULES}),
        },
    }


def _normalise_token(value: str) -> str:
    return str(value).strip().lower()