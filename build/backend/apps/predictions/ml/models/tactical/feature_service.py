from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from apps.predictions.ml.models.tactical.config import (
    TEAM_MATCH_CLUSTERS_PATH,
    TEAM_SEASON_PROFILES_PATH,
    ZONE_COUNT,
    ZONE_PROFILES_PATH,
)


logger = logging.getLogger(__name__)

DEFAULT_ROLLING_WINDOW = 10


_team_season_cache: Optional[pd.DataFrame] = None
_team_match_cache: Optional[pd.DataFrame] = None
_team_match_clusters_cache: Optional[pd.DataFrame] = None


def _load_team_season_profiles() -> pd.DataFrame:
    global _team_season_cache
    if _team_season_cache is None:
        _team_season_cache = pd.read_csv(TEAM_SEASON_PROFILES_PATH)
    return _team_season_cache


def _load_team_match_profiles() -> pd.DataFrame:
    global _team_match_cache
    if _team_match_cache is None:
        _team_match_cache = pd.read_csv(ZONE_PROFILES_PATH)
    return _team_match_cache


def _load_team_match_clusters() -> pd.DataFrame:
    global _team_match_clusters_cache
    if _team_match_clusters_cache is None:
        _team_match_clusters_cache = pd.read_csv(TEAM_MATCH_CLUSTERS_PATH)
    return _team_match_clusters_cache


def list_available_teams() -> list[str]:
    profiles = _load_team_season_profiles()
    return sorted(profiles["team_name"].unique().tolist())


def list_available_seasons_for_team(team_name: str) -> list[str]:
    profiles = _load_team_season_profiles()
    team_rows = profiles[profiles["team_name"] == team_name]
    return sorted(team_rows["season_name"].unique().tolist())


def get_team_season_profile(
    team_name: str,
    season_name: Optional[str] = None,
) -> Optional[pd.Series]:
    profiles = _load_team_season_profiles()
    team_rows = profiles[profiles["team_name"] == team_name]
    if team_rows.empty:
        return None
    if season_name:
        season_rows = team_rows[team_rows["season_name"] == season_name]
        if not season_rows.empty:
            return season_rows.iloc[0]
    return team_rows.sort_values("season_id").iloc[-1]


def get_team_season_cluster(
    team_name: str,
    season_name: Optional[str] = None,
) -> Optional[int]:
    clusters = _load_team_match_clusters()
    team_rows = clusters[clusters["team_name"] == team_name]
    if team_rows.empty:
        return None
    if season_name:
        team_rows = team_rows[team_rows["season_name"] == season_name]
        if team_rows.empty:
            return None
    mode_cluster = team_rows["cluster"].value_counts().idxmax()
    return int(mode_cluster)


def get_team_rolling_clusters(
    team_name: str,
    season_name: Optional[str] = None,
    n_recent: int = DEFAULT_ROLLING_WINDOW,
) -> Optional[pd.DataFrame]:
    clusters = _load_team_match_clusters()
    team_rows = clusters[clusters["team_name"] == team_name]
    if season_name:
        team_rows = team_rows[team_rows["season_name"] == season_name]
    if team_rows.empty:
        return None
    return team_rows.sort_values("match_id").tail(n_recent)


def get_team_rolling_zone_profile(
    team_name: str,
    season_name: Optional[str] = None,
    n_recent: int = DEFAULT_ROLLING_WINDOW,
) -> Optional[pd.Series]:
    profiles = _load_team_match_profiles()
    team_rows = profiles[profiles["team_name"] == team_name]
    if season_name:
        team_rows = team_rows[team_rows["season_name"] == season_name]
    if team_rows.empty:
        return None
    recent = team_rows.sort_values("match_id").tail(n_recent)

    feature_cols = [c for c in recent.columns if c.startswith("zone_") or c.startswith("overall_")]
    aggregated = recent[feature_cols].mean()

    aggregated["team_name"] = team_name
    aggregated["season_name"] = recent["season_name"].iloc[-1]
    aggregated["competition_name"] = recent["competition_name"].iloc[-1]
    aggregated["n_matches_aggregated"] = len(recent)
    return aggregated


def get_zone_success_dict(profile: pd.Series) -> dict[int, float]:
    return {
        zone_id: float(profile[f"zone_{zone_id}_success_rate"])
        for zone_id in range(ZONE_COUNT)
    }


def get_zone_volume_dict(profile: pd.Series) -> dict[int, float]:
    return {
        zone_id: float(profile[f"zone_{zone_id}_pass_volume"])
        for zone_id in range(ZONE_COUNT)
    }


def reset_caches() -> None:
    global _team_season_cache, _team_match_cache, _team_match_clusters_cache
    _team_season_cache = None
    _team_match_cache = None
    _team_match_clusters_cache = None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print()
    print("=== FEATURE SERVICE SMOKE TEST ===")
    teams = list_available_teams()
    print(f"Available teams: {len(teams)}")
    print(f"First 5: {teams[:5]}")

    print()
    print("Barcelona seasons:", list_available_seasons_for_team("Barcelona"))

    print()
    season_profile = get_team_season_profile("Barcelona", "2018/2019")
    print(f"Barcelona 2018/2019 season profile loaded: {season_profile is not None}")
    if season_profile is not None:
        print(f"  n_matches: {int(season_profile['n_matches'])}")
        print(f"  overall_completion_rate: {float(season_profile['overall_completion_rate']):.4f}")

    print()
    cluster = get_team_season_cluster("Barcelona", "2018/2019")
    print(f"Barcelona 2018/2019 dominant cluster: {cluster}")

    print()
    rolling = get_team_rolling_clusters("Barcelona", "2018/2019", n_recent=10)
    if rolling is not None:
        print(f"Barcelona 2018/2019 last 10 match clusters:")
        print(rolling[["match_id", "cluster"]].to_string(index=False))

    print()
    rolling_profile = get_team_rolling_zone_profile("Barcelona", "2018/2019", n_recent=10)
    if rolling_profile is not None:
        print(f"Barcelona 2018/2019 rolling profile (last 10):")
        print(f"  n_matches_aggregated: {int(rolling_profile['n_matches_aggregated'])}")
        print(f"  overall_completion_rate: {float(rolling_profile['overall_completion_rate']):.4f}")
        zones = get_zone_success_dict(rolling_profile)
        print(f"  zone 14 success: {zones[14]:.4f}")


if __name__ == "__main__":
    main()