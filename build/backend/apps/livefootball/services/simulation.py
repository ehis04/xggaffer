from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd
from django.core.cache import cache

from ml.engines.elo import INITIAL_RATING, compute_elo_history
from ml.features.rolling import (
    ALL_SEASONS,
    compute_team_rolling_features,
    load_match_history,
    to_team_match_rows,
)
from ml.models.match_outcome.config import MODEL_VERSION, resolve_latest_model_path
from ml.models.match_outcome.feature_service import get_feature_service
from ml.models.match_outcome.predict import get_predictor
from ml.models.scoreline.predict import ScorePredictor, resolve_latest_score_model
from ml.models.simulation.config import MATCHES_PER_MATCHWEEK
from ml.models.simulation.prepare_fixtures import prepare_fixture_features, prepare_remaining_fixtures
from ml.models.simulation.simulate import (
    aggregate_results,
    simulate_season,
    simulate_with_locked_results,
)


SUPPORTED_SIMULATION_MODES = {"pre_season", "current_expected", "as_of_matchweek"}
DEFAULT_SIMULATION_COUNT = 5000
SIMULATION_ENGINE_VERSION = "v1"
SIMULATION_CACHE_TTL_SECONDS = 300


logger = logging.getLogger(__name__)


def _build_simulation_cache_key(context: SimulationContext) -> str:
    matchweek_token = context.matchweek if context.matchweek is not None else "none"
    return (
        "livefootball:simulation:"
        f"{context.league}:{context.season}:{context.mode}:{context.simulation_count}:{matchweek_token}:{context.projection_window}"
    )


@dataclass(frozen=True)
class SimulationContext:
    league: str
    season: str
    mode: str
    simulation_count: int
    matchweek: int | None
    projection_window: str


@dataclass(frozen=True)
class PreparedSimulationData:
    context: SimulationContext
    all_matches_df: pd.DataFrame
    target_season_matches_df: pd.DataFrame
    historical_matches_df: pd.DataFrame
    actual_results: list[dict[str, Any]]
    remaining_fixtures: list[dict[str, Any]]
    fixture_features_df: pd.DataFrame
    strength_snapshot: dict[str, dict[str, Any]]
    based_on_matchweek: int | None
    data_cutoff_date: str | None
    freeze_timestamp: pd.Timestamp
    remaining_fixtures_source: str


def _validate_mode(mode: str) -> str:
    cleaned = str(mode).strip()
    if cleaned not in SUPPORTED_SIMULATION_MODES:
        raise ValueError(
            f"Unsupported simulation mode '{mode}'. "
            f"Expected one of: {sorted(SUPPORTED_SIMULATION_MODES)}."
        )
    return cleaned


def _validate_simulation_count(simulation_count: int) -> int:
    try:
        parsed = int(simulation_count)
    except (TypeError, ValueError) as exc:
        raise ValueError("simulation_count must be an integer.") from exc

    if parsed <= 0:
        raise ValueError("simulation_count must be greater than 0.")

    return parsed

def _validate_matchweek(mode: str, matchweek: int | None) -> int | None:
    if mode != "as_of_matchweek":
        return None

    if matchweek is None:
        raise ValueError("matchweek is required when mode is as_of_matchweek.")

    try:
        parsed = int(matchweek)
    except (TypeError, ValueError) as exc:
        raise ValueError("matchweek must be an integer.") from exc

    if parsed <= 0:
        raise ValueError("matchweek must be greater than 0.")

    return parsed


def _validate_projection_window(projection_window: str | None) -> str:
    cleaned = str(projection_window or "full_season").strip()
    if cleaned not in {"full_season", "to_date"}:
        raise ValueError("projection_window must be either 'full_season' or 'to_date'.")
    return cleaned


def _count_total_matchweeks(target_season_matches_df: pd.DataFrame) -> int:
    total_matches = len(target_season_matches_df.index)
    if total_matches == 0:
        return 0

    quotient, remainder = divmod(total_matches, MATCHES_PER_MATCHWEEK)
    return quotient + (1 if remainder else 0)

def _build_fixture_key(home_team: str, away_team: str) -> str:
    return f"{home_team}__{away_team}"


def _normalise_locked_results(
    locked_results: list[dict[str, Any]] | None,
    remaining_fixtures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fixture_lookup = {
        _build_fixture_key(fixture["home_team"], fixture["away_team"]): fixture
        for fixture in remaining_fixtures
    }

    seen_keys: set[str] = set()
    normalised: list[dict[str, Any]] = []

    for item in locked_results or []:
        fixture_key = str(item.get("fixture_key") or "").strip()
        if not fixture_key:
            raise ValueError("Each locked result requires a fixture_key.")

        if fixture_key not in fixture_lookup:
            raise ValueError(
                f"Locked result '{fixture_key}' is not part of the remaining fixture list."
            )

        if fixture_key in seen_keys:
            raise ValueError(f"Duplicate locked result for fixture '{fixture_key}'.")

        seen_keys.add(fixture_key)

        try:
            home_goals = int(item.get("home_goals"))
            away_goals = int(item.get("away_goals"))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Locked result '{fixture_key}' must include integer home_goals and away_goals."
            ) from exc

        if home_goals < 0 or away_goals < 0:
            raise ValueError(
                f"Locked result '{fixture_key}' cannot use negative goal values."
            )

        fixture = fixture_lookup[fixture_key]
        normalised.append(
            {
                "fixture_key": fixture_key,
                "home_team": fixture["home_team"],
                "away_team": fixture["away_team"],
                "home_goals": home_goals,
                "away_goals": away_goals,
            }
        )

    return normalised

def _latest_available_season_label(
    all_matches_df: pd.DataFrame,
    *,
    league: str,
) -> str:
    league_rows = all_matches_df[all_matches_df["league"] == league].copy()
    if league_rows.empty:
        raise ValueError(f"No match history found for league '{league}'.")

    season_labels = league_rows["season"].astype(str).tolist()
    numeric_labels = [int(label) for label in season_labels if label.isdigit()]

    if numeric_labels:
        return str(max(numeric_labels))

    return max(season_labels)

def _build_context(
    league: str,
    season: str,
    mode: str,
    simulation_count: int,
    matchweek: int | None = None,
    projection_window: str | None = None,
) -> SimulationContext:
    cleaned_league = str(league).strip()
    cleaned_season = str(season).strip()

    if not cleaned_league:
        raise ValueError("league is required.")
    if not cleaned_season:
        raise ValueError("season is required.")

    cleaned_mode = _validate_mode(mode)

    return SimulationContext(
        league=cleaned_league,
        season=cleaned_season,
        mode=cleaned_mode,
        simulation_count=_validate_simulation_count(simulation_count),
        matchweek=_validate_matchweek(cleaned_mode, matchweek),
        projection_window=_validate_projection_window(projection_window),
    )


def _resolve_engine_versions() -> dict[str, str]:
    outcome_model_path = resolve_latest_model_path(strict=False)

    try:
        score_model_path = resolve_latest_score_model()
        score_version = score_model_path.stem
    except FileNotFoundError:
        score_version = "unavailable"

    return {
        "elo": "v1",
        "outcome": MODEL_VERSION if outcome_model_path is not None else "unavailable",
        "score": score_version,
        "simulation": SIMULATION_ENGINE_VERSION,
    }


def _load_simulation_match_history(league: str) -> pd.DataFrame:
    matches = load_match_history(leagues=[league], seasons=ALL_SEASONS).copy()
    matches["date"] = pd.to_datetime(matches["date"])
    matches["season"] = matches["season"].astype(str)
    matches["league"] = matches["league"].astype(str)

    return matches.sort_values(["date", "match_id"]).reset_index(drop=True)


def _get_target_season_matches(
    all_matches_df: pd.DataFrame,
    *,
    league: str,
    season: str,
) -> pd.DataFrame:
    target = all_matches_df[
        (all_matches_df["league"] == league)
        & (all_matches_df["season"] == season)
    ].copy()

    if target.empty:
        raise ValueError(f"No match data found for {league} {season}.")

    return target.sort_values(["date", "match_id"]).reset_index(drop=True)


def _extract_target_teams(target_season_matches_df: pd.DataFrame) -> list[str]:
    teams = set(target_season_matches_df["home_team"].tolist()) | set(
        target_season_matches_df["away_team"].tolist()
    )
    return sorted(teams)


def _played_fixture_pairs(target_season_matches_df: pd.DataFrame) -> set[tuple[str, str]]:
    played_rows = target_season_matches_df[
        target_season_matches_df["home_goals"].notna()
        & target_season_matches_df["away_goals"].notna()
    ]
    return {
        (str(row["home_team"]), str(row["away_team"]))
        for _, row in played_rows.iterrows()
    }


def _build_synthetic_remaining_fixtures(
    target_season_matches_df: pd.DataFrame,
    *,
    freeze_timestamp: pd.Timestamp,
) -> pd.DataFrame:
    teams = _extract_target_teams(target_season_matches_df)
    if len(teams) < 2:
        return pd.DataFrame(columns=["home_team", "away_team", "date"])

    played_pairs = _played_fixture_pairs(target_season_matches_df)
    remaining_rows: list[dict[str, Any]] = []

    for home_team in teams:
        for away_team in teams:
            if home_team == away_team:
                continue
            if (home_team, away_team) in played_pairs:
                continue

            remaining_rows.append(
                {
                    "home_team": home_team,
                    "away_team": away_team,
                    "date": freeze_timestamp,
                }
            )

    if not remaining_rows:
        return pd.DataFrame(columns=["home_team", "away_team", "date"])

    return pd.DataFrame(remaining_rows)


def _build_synthetic_full_season_fixtures(
    teams: list[str],
    *,
    fixture_date: pd.Timestamp,
) -> pd.DataFrame:
    if len(teams) < 2:
        return pd.DataFrame(columns=["home_team", "away_team", "date"])

    rows: list[dict[str, Any]] = []
    for home_team in teams:
        for away_team in teams:
            if home_team == away_team:
                continue
            rows.append(
                {
                    "home_team": home_team,
                    "away_team": away_team,
                    "date": fixture_date,
                }
            )

    if not rows:
        return pd.DataFrame(columns=["home_team", "away_team", "date"])

    return pd.DataFrame(rows)


def _derive_based_on_matchweek_from_actual_results(
    actual_results: list[dict[str, Any]],
) -> int | None:
    played_matches = len(actual_results)
    if played_matches <= 0:
        return 0

    if played_matches % MATCHES_PER_MATCHWEEK == 0:
        return played_matches // MATCHES_PER_MATCHWEEK

    return None


def _build_strength_snapshot(
    historical_matches_df: pd.DataFrame,
    *,
    target_teams: list[str],
    cutoff_date: pd.Timestamp,
) -> dict[str, dict[str, Any]]:
    ordered_historical = historical_matches_df.sort_values(["date", "match_id"]).copy()

    if ordered_historical.empty:
        return {
            team: {
                "elo": float(INITIAL_RATING),
                "rolling_features": {},
            }
            for team in target_teams
        }

    elo_history_rows, current_elos = compute_elo_history(ordered_historical)
    _ = elo_history_rows
    team_match_rows = to_team_match_rows(ordered_historical)

    snapshot: dict[str, dict[str, Any]] = {}

    for team in target_teams:
        team_history = team_match_rows[team_match_rows["team"] == team].sort_values("date")
        rolling_features = compute_team_rolling_features(team_history, cutoff_date)

        snapshot[team] = {
            "elo": float(current_elos.get(team, INITIAL_RATING)),
            "rolling_features": rolling_features,
        }

    return snapshot


def _prepare_pre_season_data(
    context: SimulationContext,
    all_matches_df: pd.DataFrame,
    target_season_matches_df: pd.DataFrame,
) -> PreparedSimulationData:
    actual_results, remaining_fixtures, fixture_features_df = prepare_remaining_fixtures(
        all_matches_df,
        context.season,
        context.league,
        freeze_matchweek=0,
    )

    freeze_timestamp = target_season_matches_df["date"].min()
    historical_matches_df = all_matches_df[all_matches_df["date"] < freeze_timestamp].copy()
    target_teams = _extract_target_teams(target_season_matches_df)
    expected_fixture_count = len(target_teams) * (len(target_teams) - 1)

    remaining_fixtures_source = "historical_schedule"
    if len(remaining_fixtures) < expected_fixture_count:
        synthetic_full_schedule_df = _build_synthetic_full_season_fixtures(
            target_teams,
            fixture_date=freeze_timestamp,
        )
        if not synthetic_full_schedule_df.empty:
            remaining_fixtures = synthetic_full_schedule_df[
                ["home_team", "away_team"]
            ].to_dict("records")
            fixture_features_df = prepare_fixture_features(
                all_matches_df,
                synthetic_full_schedule_df,
                freeze_timestamp,
            )
            remaining_fixtures_source = "synthetic_round_robin_full_season"
            logger.warning(
                "Incomplete fixture schedule for %s %s pre-season full_season projection; "
                "synthesized %s fixtures (expected %s).",
                context.league,
                context.season,
                len(remaining_fixtures),
                expected_fixture_count,
            )

    return PreparedSimulationData(
        context=context,
        all_matches_df=all_matches_df,
        target_season_matches_df=target_season_matches_df,
        historical_matches_df=historical_matches_df,
        actual_results=actual_results,
        remaining_fixtures=remaining_fixtures,
        fixture_features_df=fixture_features_df,
        strength_snapshot=_build_strength_snapshot(
            historical_matches_df,
            target_teams=target_teams,
            cutoff_date=freeze_timestamp,
        ),
        based_on_matchweek=0,
        data_cutoff_date=freeze_timestamp.date().isoformat(),
        freeze_timestamp=freeze_timestamp,
        remaining_fixtures_source=remaining_fixtures_source,
    )


def _latest_played_match_date(target_season_matches_df: pd.DataFrame) -> pd.Timestamp | None:
    played_mask = (
        target_season_matches_df["home_goals"].notna()
        & target_season_matches_df["away_goals"].notna()
    )
    if not played_mask.any():
        return None

    return target_season_matches_df.loc[played_mask, "date"].max()


def _prepare_pre_season_to_date_data(
    context: SimulationContext,
    all_matches_df: pd.DataFrame,
    target_season_matches_df: pd.DataFrame,
) -> PreparedSimulationData:
    season_start = target_season_matches_df["date"].min()
    latest_played_date = _latest_played_match_date(target_season_matches_df)
    if latest_played_date is None:
        raise ValueError(
            f"No played matches are available yet for {context.league} {context.season}."
        )

    fixtures_to_date_df = target_season_matches_df[
        (target_season_matches_df["date"] <= latest_played_date)
        & target_season_matches_df["home_goals"].notna()
        & target_season_matches_df["away_goals"].notna()
    ].copy()

    historical_matches_df = all_matches_df[all_matches_df["date"] < season_start].copy()
    target_teams = _extract_target_teams(target_season_matches_df)

    fixture_features_df = prepare_fixture_features(
        all_matches_df,
        fixtures_to_date_df,
        season_start,
    )
    remaining_fixtures = fixtures_to_date_df[["home_team", "away_team"]].to_dict("records")

    played_match_count = len(fixtures_to_date_df.index)
    quotient, remainder = divmod(played_match_count, MATCHES_PER_MATCHWEEK)
    based_on_matchweek = quotient if remainder == 0 else None

    return PreparedSimulationData(
        context=context,
        all_matches_df=all_matches_df,
        target_season_matches_df=target_season_matches_df,
        historical_matches_df=historical_matches_df,
        actual_results=[],
        remaining_fixtures=remaining_fixtures,
        fixture_features_df=fixture_features_df,
        strength_snapshot=_build_strength_snapshot(
            historical_matches_df,
            target_teams=target_teams,
            cutoff_date=season_start,
        ),
        based_on_matchweek=based_on_matchweek,
        data_cutoff_date=latest_played_date.date().isoformat(),
        freeze_timestamp=season_start,
        remaining_fixtures_source="historical_schedule",
    )

def _prepare_current_expected_data(
    context: SimulationContext,
    all_matches_df: pd.DataFrame,
    target_season_matches_df: pd.DataFrame,
) -> PreparedSimulationData:
    latest_played_date = _latest_played_match_date(target_season_matches_df)
    if latest_played_date is None:
        freeze_timestamp = target_season_matches_df["date"].min()
    else:
        freeze_timestamp = latest_played_date + pd.Timedelta(days=1)

    actual_results, remaining_fixtures, fixture_features_df = prepare_remaining_fixtures(
        all_matches_df,
        context.season,
        context.league,
        freeze_date=freeze_timestamp,
    )

    remaining_fixtures_source = "historical_schedule"
    if not remaining_fixtures:
        synthetic_remaining_df = _build_synthetic_remaining_fixtures(
            target_season_matches_df,
            freeze_timestamp=freeze_timestamp,
        )
        if not synthetic_remaining_df.empty:
            remaining_fixtures = synthetic_remaining_df[
                ["home_team", "away_team"]
            ].to_dict("records")
            fixture_features_df = prepare_fixture_features(
                all_matches_df,
                synthetic_remaining_df,
                freeze_timestamp,
            )
            remaining_fixtures_source = "synthetic_round_robin"
            logger.warning(
                "No explicit remaining fixtures found for %s %s; synthesized %s remaining fixtures.",
                context.league,
                context.season,
                len(remaining_fixtures),
            )

    historical_matches_df = all_matches_df[all_matches_df["date"] < freeze_timestamp].copy()
    target_teams = _extract_target_teams(target_season_matches_df)

    return PreparedSimulationData(
        context=context,
        all_matches_df=all_matches_df,
        target_season_matches_df=target_season_matches_df,
        historical_matches_df=historical_matches_df,
        actual_results=actual_results,
        remaining_fixtures=remaining_fixtures,
        fixture_features_df=fixture_features_df,
        strength_snapshot=_build_strength_snapshot(
            historical_matches_df,
            target_teams=target_teams,
            cutoff_date=freeze_timestamp,
        ),
        based_on_matchweek=_derive_based_on_matchweek_from_actual_results(actual_results),
        data_cutoff_date=freeze_timestamp.date().isoformat(),
        freeze_timestamp=freeze_timestamp,
        remaining_fixtures_source=remaining_fixtures_source,
    )

def _prepare_as_of_matchweek_data(
    context: SimulationContext,
    all_matches_df: pd.DataFrame,
    target_season_matches_df: pd.DataFrame,
) -> PreparedSimulationData:
    if context.matchweek is None:
        raise ValueError("matchweek is required when mode is as_of_matchweek.")

    total_matchweeks = _count_total_matchweeks(target_season_matches_df)
    if total_matchweeks == 0:
        raise ValueError(f"No fixtures are available for {context.league} {context.season}.")

    if context.matchweek > total_matchweeks:
        raise ValueError(
            f"matchweek must be between 1 and {total_matchweeks} for "
            f"{context.league} {context.season}."
        )

    actual_results, remaining_fixtures, fixture_features_df = prepare_remaining_fixtures(
        all_matches_df,
        context.season,
        context.league,
        freeze_matchweek=context.matchweek,
    )

    played_match_count = len(actual_results)
    if played_match_count == 0:
        raise ValueError(
            f"No played matches were found at matchweek {context.matchweek} "
            f"for {context.league} {context.season}."
        )

    played_matches_df = target_season_matches_df.iloc[:played_match_count].copy()
    last_played_match_date = played_matches_df["date"].max()
    freeze_timestamp = last_played_match_date + pd.Timedelta(days=1)

    historical_matches_df = all_matches_df[all_matches_df["date"] < freeze_timestamp].copy()
    target_teams = _extract_target_teams(target_season_matches_df)

    return PreparedSimulationData(
        context=context,
        all_matches_df=all_matches_df,
        target_season_matches_df=target_season_matches_df,
        historical_matches_df=historical_matches_df,
        actual_results=actual_results,
        remaining_fixtures=remaining_fixtures,
        fixture_features_df=fixture_features_df,
        strength_snapshot=_build_strength_snapshot(
            historical_matches_df,
            target_teams=target_teams,
            cutoff_date=freeze_timestamp,
        ),
        based_on_matchweek=context.matchweek,
        data_cutoff_date=last_played_match_date.date().isoformat(),
        freeze_timestamp=freeze_timestamp,
        remaining_fixtures_source="historical_schedule",
    )


def _prepare_simulation_data(
    context: SimulationContext,
) -> PreparedSimulationData:
    all_matches_df = _load_simulation_match_history(context.league)
    target_season_matches_df = _get_target_season_matches(
        all_matches_df,
        league=context.league,
        season=context.season,
    )

    if context.mode == "pre_season":
        if context.projection_window == "to_date":
            return _prepare_pre_season_to_date_data(
                context,
                all_matches_df,
                target_season_matches_df,
            )

        return _prepare_pre_season_data(
            context,
            all_matches_df,
            target_season_matches_df,
        )

    if context.mode == "as_of_matchweek":
        return _prepare_as_of_matchweek_data(
            context,
            all_matches_df,
            target_season_matches_df,
        )

    return _prepare_current_expected_data(
        context,
        all_matches_df,
        target_season_matches_df,
    )

def _build_fixture_outcome_probabilities(
    prepared: PreparedSimulationData,
) -> list[dict[str, Any]]:
    if not prepared.remaining_fixtures:
        return []

    cutoff_timestamp = prepared.freeze_timestamp
    service = get_feature_service(leagues=[prepared.context.league], seasons=ALL_SEASONS)
    predictor = get_predictor()

    rows: list[dict[str, Any]] = []
    market_columns = ["market_home_prob", "market_draw_prob", "market_away_prob"]
    skipped_enrichment_count = 0

    for fixture in prepared.remaining_fixtures:
        try:
            features = service.build_prediction_features(
                home_team=fixture["home_team"],
                away_team=fixture["away_team"],
                league=prepared.context.league,
                season=prepared.context.season,
                as_of=cutoff_timestamp,
                use_cache=False,
            )

            required_columns = set(predictor.feature_columns)
            missing_market_columns = [col for col in market_columns if col not in features.columns]

            if missing_market_columns and any(col in required_columns for col in market_columns):
                for col in market_columns:
                    if col not in features.columns:
                        features[col] = 1.0 / 3.0

                market_sum = (
                    features["market_home_prob"]
                    + features["market_draw_prob"]
                    + features["market_away_prob"]
                )
                market_sum = market_sum.where(market_sum > 0, other=1.0)
                for col in market_columns:
                    features[col] = features[col] / market_sum

            result = predictor.predict(features)
        except Exception as exc:
            logger.debug(
                "Skipping outcome probability enrichment for %s vs %s (%s)",
                fixture["home_team"],
                fixture["away_team"],
                exc,
            )
            skipped_enrichment_count += 1
            continue

        rows.append(
            {
                "home_team": fixture["home_team"],
                "away_team": fixture["away_team"],
                "prediction": result["prediction"],
                "probabilities": result["probabilities"],
            }
        )

    if skipped_enrichment_count:
        logger.warning(
            "Skipped outcome probability enrichment for %s fixture(s) due to incomplete prediction features.",
            skipped_enrichment_count,
        )

    return rows


def _predict_score_lambdas(
    prepared: PreparedSimulationData,
) -> tuple[pd.Series | list[float], pd.Series | list[float]]:
    if prepared.fixture_features_df.empty:
        return [], []

    predictor = ScorePredictor()
    return predictor.predict_lambdas_batch(prepared.fixture_features_df)


def _shape_expected_table(aggregated_df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for _, row in aggregated_df.iterrows():
        rows.append(
            {
                "team": row["team"],
                "predicted_points": round(float(row["projected_points_mean"]), 2),
                "predicted_position": int(row["modal_position"]),
                "position_probabilities": {
                    int(position): round(float(probability), 4)
                    for position, probability in row["position_probs"].items()
                },
                "title_probability": round(float(row["p_title"]), 4),
                "top_4_probability": round(float(row["p_top_4"]), 4),
                "relegation_probability": round(float(row["p_relegation"]), 4),
                "simulated_wins": round(float(row["simulated_wins"]), 2),
                "simulated_draws": round(float(row["simulated_draws"]), 2),
                "simulated_losses": round(float(row["simulated_losses"]), 2),
                "simulated_goals_for": round(float(row["simulated_goals_for"]), 2),
                "simulated_goals_against": round(float(row["simulated_goals_against"]), 2),
            }
        )

    rows.sort(
        key=lambda item: (
            -item["predicted_points"],
            item["predicted_position"],
            item["team"],
        )
    )
    return rows


def _run_simulation(prepared: PreparedSimulationData) -> list[dict[str, Any]]:
    _ = _build_fixture_outcome_probabilities(prepared)

    lambda_home, lambda_away = _predict_score_lambdas(prepared)

    sim_output = simulate_season(
        actual_results=prepared.actual_results,
        remaining_fixtures=prepared.remaining_fixtures,
        lambda_home=lambda_home,
        lambda_away=lambda_away,
        n_simulations=prepared.context.simulation_count,
    )
    aggregated_df = aggregate_results(sim_output)
    return _shape_expected_table(aggregated_df)


def simulate_league_season(
    league: str,
    season: str,
    mode: str,
    simulation_count: int = DEFAULT_SIMULATION_COUNT,
    matchweek: int | None = None,
    projection_window: str | None = None,
) -> dict[str, Any]:
    context = _build_context(
        league=league,
        season=season,
        mode=mode,
        simulation_count=simulation_count,
        matchweek=matchweek,
        projection_window=projection_window,
    )
    cache_key = _build_simulation_cache_key(context)
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return cached_payload

    prepared = _prepare_simulation_data(context)
    expected_table = _run_simulation(prepared)

    payload = {
        "league": prepared.context.league,
        "season": prepared.context.season,
        "mode": prepared.context.mode,
        "projection_window": prepared.context.projection_window,
        "simulation_count": prepared.context.simulation_count,
        "based_on_matchweek": prepared.based_on_matchweek,
        "data_cutoff_date": prepared.data_cutoff_date,
        "expected_table": expected_table,
        "metadata": {
            "engine_versions": _resolve_engine_versions(),
            "total_fixtures_simulated": len(prepared.remaining_fixtures) * prepared.context.simulation_count,
            "remaining_fixtures": len(prepared.remaining_fixtures),
            "remaining_fixtures_source": prepared.remaining_fixtures_source,
            "total_matchweeks": _count_total_matchweeks(prepared.target_season_matches_df),
            "projection_window": prepared.context.projection_window,
        },
    }
    cache.set(cache_key, payload, timeout=SIMULATION_CACHE_TTL_SECONDS)
    return payload

def simulate_league_scenario(
    league: str,
    season: str,
    mode: str,
    locked_results: list[dict[str, Any]] | None = None,
    simulation_count: int = DEFAULT_SIMULATION_COUNT,
    matchweek: int | None = None,
) -> dict[str, Any]:
    context = _build_context(
        league=league,
        season=season,
        mode=mode,
        simulation_count=simulation_count,
        matchweek=matchweek,
    )
    prepared = _prepare_simulation_data(context)

    normalised_locked_results = _normalise_locked_results(
        locked_results=locked_results,
        remaining_fixtures=prepared.remaining_fixtures,
    )

    _ = _build_fixture_outcome_probabilities(prepared)
    lambda_home, lambda_away = _predict_score_lambdas(prepared)

    sim_output = simulate_with_locked_results(
        actual_results=prepared.actual_results,
        remaining_fixtures=prepared.remaining_fixtures,
        lambda_home=lambda_home,
        lambda_away=lambda_away,
        locked_results=[
            {
                "home_team": item["home_team"],
                "away_team": item["away_team"],
                "home_goals": item["home_goals"],
                "away_goals": item["away_goals"],
            }
            for item in normalised_locked_results
        ],
        n_simulations=prepared.context.simulation_count,
    )
    aggregated_df = aggregate_results(sim_output)
    expected_table = _shape_expected_table(aggregated_df)

    remaining_fixture_rows = [
        {
            "fixture_key": _build_fixture_key(fixture["home_team"], fixture["away_team"]),
            "home_team": fixture["home_team"],
            "away_team": fixture["away_team"],
        }
        for fixture in prepared.remaining_fixtures
    ]

    locked_count = len(normalised_locked_results)
    remaining_after_lock = max(len(prepared.remaining_fixtures) - locked_count, 0)

    return {
        "league": prepared.context.league,
        "season": prepared.context.season,
        "mode": prepared.context.mode,
        "simulation_count": prepared.context.simulation_count,
        "based_on_matchweek": prepared.based_on_matchweek,
        "data_cutoff_date": prepared.data_cutoff_date,
        "remaining_fixtures": remaining_fixture_rows,
        "locked_results": normalised_locked_results,
        "expected_table": expected_table,
        "metadata": {
            "engine_versions": _resolve_engine_versions(),
            "remaining_fixtures_before_lock": len(prepared.remaining_fixtures),
            "remaining_fixtures_after_lock": remaining_after_lock,
            "remaining_fixtures": remaining_after_lock,
            "total_fixtures_simulated": remaining_after_lock * prepared.context.simulation_count,
            "remaining_fixtures_source": prepared.remaining_fixtures_source,
            "total_matchweeks": _count_total_matchweeks(prepared.target_season_matches_df),
        },
    }