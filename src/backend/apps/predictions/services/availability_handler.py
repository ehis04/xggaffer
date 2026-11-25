from __future__ import annotations

import logging
import threading
from datetime import date as date_type

import pandas as pd

from apps.predictions.data_paths import PROCESSED_DATA_ROOT
from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.source_policy import (
    apply_source_priority,
    latest_available_season,
    source_coverage_metadata,
)

_logger = logging.getLogger(__name__)

DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = "2025"

PLAYERS_CSV_PATH = (
    PROCESSED_DATA_ROOT
    / "players"
    / "merged"
    / "all_leagues_all_seasons_players_merged.csv"
)

LINEUP_FEATURES_PATH = PROCESSED_DATA_ROOT / "lineup_features.csv"

INJURY_SPELLS_PATH = PROCESSED_DATA_ROOT / "injury_spells.csv"

_RISK_DEFAULTS: dict[str, float] = {
    "minutes_last_7d": 0.0,
    "minutes_last_14d": 0.0,
    "minutes_last_30d": 0.0,
    "matches_last_7d": 0.0,
    "matches_last_14d": 0.0,
    "consecutive_starts": 0.0,
    "days_since_last_rest": 0.0,
    "age": 25.0,
    "prior_injuries_count": 0.0,
    "days_since_last_injury": 0.0,
    "season_phase_mid": 0.0,
    "season_phase_late": 1.0,
    "acwr_7_28": 1.0,
    "minutes_per_match_30d": 0.0,
    "workload_zscore_30d": 0.0,
    "recent_match_density": 0.0,
    "cumulative_workload_per_week": 0.0,
    "has_prior_injury": 0.0,
    "has_recent_rest": 0.0,
}


def _csv_float(v, default: float = 0.0) -> float:
    try:
        f = float(v)
        return f if f == f else default  # f != f is True only for NaN
    except (TypeError, ValueError):
        return default


_open_injury_index: "dict[int, dict] | None" = None
_injury_index_lock = threading.Lock()

# Columns needed from lineup_features.csv for availability risk scoring
_LINEUP_USECOLS = [
    "match_id", "date", "season", "league", "team_name", "player_id", "player_name",
    "minutes_last_match", "minutes_last_3_matches", "minutes_last_5_matches",
    "consecutive_starts", "days_since_last_start", "days_since_last_appearance",
    "season_phase",
]


def _load_lineup_features() -> "pd.DataFrame | None":
    """Reuse the feature_service cache to avoid a second 500 MB load."""
    try:
        from apps.predictions.ml.models.lineup.feature_service import _load_features
        return _load_features()
    except Exception:
        pass
    # Direct fallback when the lineup model isn't available
    if not LINEUP_FEATURES_PATH.exists():
        return None
    return pd.read_csv(LINEUP_FEATURES_PATH, usecols=_LINEUP_USECOLS)


def _load_open_injury_index() -> "dict[int, dict]":
    """Return a dict keyed by understat_player_id for currently-injured players."""
    global _open_injury_index
    if _open_injury_index is not None:
        return _open_injury_index

    with _injury_index_lock:
        if _open_injury_index is not None:
            return _open_injury_index

        _open_injury_index = {}
        if not INJURY_SPELLS_PATH.exists():
            return _open_injury_index

        df = pd.read_csv(INJURY_SPELLS_PATH)
        open_spells = df[df["is_open_spell"] == True]
        for _, row in open_spells.iterrows():
            uid = row.get("understat_player_id")
            if uid is None or (isinstance(uid, float) and uid != uid):
                continue
            uid = int(uid)
            _open_injury_index[uid] = {
                "injury_start_date": str(row.get("start_date") or ""),
                "injury_type_category": str(row.get("injury_type_category") or "OTHER"),
            }
        return _open_injury_index


def _build_player_row(player_name: str, team: str | None) -> dict:
    row = dict(_RISK_DEFAULTS)
    row["player_id"] = None
    row["player_name"] = player_name
    row["team"] = team or ""
    row["is_injured"] = False
    return row


def _workload_features_from_lineup_row(player_row: pd.Series) -> dict:
    """Map lineup_features.csv columns to availability risk model features."""
    mins_last = _csv_float(player_row.get("minutes_last_match"))
    mins_last3 = _csv_float(player_row.get("minutes_last_3_matches"))
    mins_last5 = _csv_float(player_row.get("minutes_last_5_matches"))
    consec = _csv_float(player_row.get("consecutive_starts"))
    days_since_start = _csv_float(player_row.get("days_since_last_start"), default=999.0)
    days_since_app = _csv_float(player_row.get("days_since_last_appearance"), default=999.0)
    phase = int(_csv_float(player_row.get("season_phase")))

    mpg = mins_last5 / 5.0 if mins_last5 > 0 else 0.0
    chronic = mpg
    acwr = (mins_last / chronic) if chronic > 0 else 1.0
    est_matches_14d = min((mins_last3 / mpg) if mpg > 0 else 0.0, 4.0)

    return {
        "minutes_last_7d": mins_last,
        "minutes_last_14d": mins_last3,
        "minutes_last_30d": mins_last5,
        "matches_last_7d": 1.0 if mins_last > 30 else 0.0,
        "matches_last_14d": est_matches_14d,
        "consecutive_starts": consec,
        "days_since_last_rest": days_since_app,
        "minutes_per_match_30d": mpg,
        "workload_zscore_30d": min(max((mpg - 60.0) / 30.0, -2.0), 2.0),
        "recent_match_density": min(est_matches_14d / 2.0, 2.0),
        "cumulative_workload_per_week": mpg,
        "acwr_7_28": min(max(acwr, 0.0), 3.0),
        "has_recent_rest": 1.0 if days_since_start > 7 else 0.0,
        "season_phase_mid": 1.0 if phase == 1 else 0.0,
        "season_phase_late": 1.0 if phase >= 2 else 0.0,
    }


def _apply_injury_status(row: dict, injury_index: "dict[int, dict]") -> None:
    """Mutate row in-place with injury data if the player has an open spell."""
    uid = row.get("player_id")
    if uid is None:
        return
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        return
    spell = injury_index.get(uid)
    if spell:
        row["is_injured"] = True
        row["injury_start_date"] = spell["injury_start_date"]
        row["injury_type_category"] = spell["injury_type_category"]


def _get_team_squad(team: str, league: str, season: str) -> tuple[list[dict], list[str]]:
    season_int = int(season)
    injury_index = _load_open_injury_index()

    lineup_df = _load_lineup_features()
    if lineup_df is not None:
        subset = lineup_df[
            (lineup_df["team_name"] == team)
            & (lineup_df["league"] == league)
            & (lineup_df["season"] == season_int)
        ]
        if not subset.empty:
            # One row per player from their most recent match
            latest_per_player = (
                subset.sort_values("date")
                .groupby("player_id", sort=False)
                .last()
                .reset_index()
            )
            rows = []
            for _, player_row in latest_per_player.iterrows():
                row = dict(_RISK_DEFAULTS)
                row.update(_workload_features_from_lineup_row(player_row))
                row["player_id"] = player_row.get("player_id")
                row["player_name"] = str(player_row.get("player_name", ""))
                row["team"] = team
                row["is_injured"] = False
                _apply_injury_status(row, injury_index)
                rows.append(row)
            return rows, ["lineup_features"]

    # Fallback: season-level players CSV (no workload data available)
    if not PLAYERS_CSV_PATH.exists():
        return [], []

    df = pd.read_csv(PLAYERS_CSV_PATH)
    subset = df[
        (df["team"] == team)
        & (df["league"] == league)
        & (df["season"] == season_int)
    ]
    subset, used_sources = apply_source_priority(
        subset,
        dedupe_keys=["season", "league", "team", "name"],
    )
    rows = []
    for _, player_row in subset.iterrows():
        row = dict(_RISK_DEFAULTS)
        row["player_id"] = player_row.get("player_id")
        row["player_name"] = str(player_row.get("name", ""))
        row["team"] = team
        row["is_injured"] = False
        _apply_injury_status(row, injury_index)
        rows.append(row)
    return rows, used_sources


class AvailabilityHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        target_date = date_type.today()
        league = parsed_query.league or DEFAULT_LEAGUE
        try:
            season = parsed_query.season
            if season is None:
                _path = LINEUP_FEATURES_PATH if LINEUP_FEATURES_PATH.exists() else PLAYERS_CSV_PATH
                if _path.exists():
                    season = latest_available_season(pd.read_csv(_path), default=DEFAULT_SEASON)
            season = season or DEFAULT_SEASON

            from apps.predictions.ml.models.availability.predict import AvailabilityPredictor

            predictor = AvailabilityPredictor()
            used_sources: list[str] = []

            if parsed_query.player_name:
                player_rows = [_build_player_row(parsed_query.player_name, parsed_query.team)]
            elif parsed_query.team:
                player_rows, used_sources = _get_team_squad(parsed_query.team, league, season)
                if not player_rows:
                    return QueryPayload(
                        intent=IntentClass.AVAILABILITY_QUERY,
                        engine_data={},
                        partial=True,
                        error=f"No player data found for {parsed_query.team} in {league} {season}.",
                    )
            else:
                return QueryPayload(
                    intent=IntentClass.AVAILABILITY_QUERY,
                    engine_data={},
                    partial=True,
                    error="No player or team specified.",
                )

            players_df = pd.DataFrame(player_rows)
            results = predictor.predict_for_players(players_df, target_date)

            return QueryPayload(
                intent=IntentClass.AVAILABILITY_QUERY,
                engine_data={
                    "players": results,
                    "team": parsed_query.team,
                    "season": season,
                    "source_coverage": source_coverage_metadata(
                        intent=IntentClass.AVAILABILITY_QUERY.value,
                        used_sources=used_sources,
                    ),
                },
                partial=False,
                error=None,
            )
        except FileNotFoundError:
            return QueryPayload(
                intent=IntentClass.AVAILABILITY_QUERY,
                engine_data={},
                partial=True,
                error="Availability model not available.",
            )
        except Exception as exc:
            _logger.exception("AvailabilityHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.AVAILABILITY_QUERY,
                engine_data={},
                partial=True,
                error=str(exc),
            )
