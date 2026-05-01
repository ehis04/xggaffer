from __future__ import annotations

import logging

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.source_policy import source_coverage_metadata
from common.utils import current_football_season

_logger = logging.getLogger(__name__)

ZONE_COUNT = 24
DOMINANT_ZONE_COUNT = 5
_TACTICAL_CLUSTER_LABELS = {
    0: "elite_final_third_possession",
    1: "league_average_buildup",
    2: "deep_central_control",
}
_UNKNOWN_CLUSTER_LABEL = "unknown"


def _latest_requested_season() -> str | None:
    season = current_football_season()
    if season:
        return season
    return "2025"


def _season_matches_requested(profile_season: str | None, requested_season: str | None) -> bool:
    if not profile_season or not requested_season:
        return True
    req = requested_season.strip().lower().replace(" ", "")
    prof = profile_season.strip().lower().replace(" ", "")
    if req == prof:
        return True
    if len(req) == 4 and req.isdigit():
        start = req[:2]
        end = req[2:]
        if prof in {f"20{start}/20{end}", f"20{start}-20{end}", f"20{start}-{end}"}:
            return True
    return False


def _season_display(value: str | None) -> str:
    if not value:
        return "latest"
    v = str(value).strip()
    if len(v) == 4 and v.isdigit():
        return f"{v[-2:]}/{str(int(v) + 1)[-2:]}"
    return v


def _fallback_note(requested: str | None, used: str | None) -> str | None:
    if not requested or not used:
        return None
    if _season_matches_requested(used, requested):
        return None
    return (
        f"{_season_display(requested)} tactical data not available; "
        f"using {_season_display(used)} instead."
    )


def _dominant_zones_from_profile(profile: pd.Series) -> list[int]:
    volume_cols = [f"zone_{i}_pass_volume" for i in range(ZONE_COUNT)]
    available_cols = [c for c in volume_cols if c in profile.index]
    if not available_cols:
        return []
    ranked = profile[available_cols].astype(float).sort_values(ascending=False)
    return [int(col.split("_")[1]) for col in ranked.head(DOMINANT_ZONE_COUNT).index]


def _cluster_label_for_profile(team_name: str, season_name: str | None) -> str:
    try:
        from apps.predictions.ml.models.tactical.feature_service import get_team_season_cluster

        cluster_id = get_team_season_cluster(team_name, season_name)
        if cluster_id is None:
            return _UNKNOWN_CLUSTER_LABEL
        return _TACTICAL_CLUSTER_LABELS.get(int(cluster_id), _UNKNOWN_CLUSTER_LABEL)
    except Exception:
        return _UNKNOWN_CLUSTER_LABEL


def _fallback_single_profile(team_name: str, requested_season: str | None) -> dict | None:
    from apps.predictions.ml.models.tactical.feature_service import get_team_season_profile

    profile = get_team_season_profile(team_name, requested_season)
    if profile is None:
        return None

    season_name = str(profile.get("season_name", "")) or None
    cluster_label = _cluster_label_for_profile(team_name, season_name)

    return {
        "query_type": "single",
        "team": team_name,
        "requested_season": requested_season,
        "profile_season": season_name,
        "season_name": season_name,
        "competition_name": profile.get("competition_name"),
        "n_matches_in_profile": int(profile.get("n_matches", 0) or 0),
        "cluster_label": cluster_label,
        "style_label": cluster_label,
        "overall_completion_rate": float(profile.get("overall_completion_rate", 0.0) or 0.0),
        "overall_forward_ratio": float(profile.get("overall_forward_ratio", 0.0) or 0.0),
        "overall_pass_length": float(profile.get("overall_pass_length", 0.0) or 0.0),
        "dominant_zones": _dominant_zones_from_profile(profile),
    }


def _fallback_compare_profiles(home_team: str, away_team: str, requested_season: str | None) -> dict | None:
    home = _fallback_single_profile(home_team, requested_season)
    away = _fallback_single_profile(away_team, requested_season)
    if home is None or away is None:
        return None

    home_zones = set(home.get("dominant_zones", []))
    away_zones = set(away.get("dominant_zones", []))
    union = home_zones | away_zones
    intersection = home_zones & away_zones
    style_similarity = float(len(intersection) / len(union)) if union else 0.0

    if style_similarity >= 0.85:
        matchup_type = "mirror"
    elif style_similarity <= 0.5:
        matchup_type = "contrast"
    else:
        matchup_type = "neutral"

    return {
        "query_type": "comparison",
        "home_team": home_team,
        "away_team": away_team,
        "requested_season": requested_season,
        "profile_season_home": home.get("season_name"),
        "profile_season_away": away.get("season_name"),
        "team_a": {
            "team": home_team,
            "season_name": home.get("season_name"),
            "competition_name": home.get("competition_name"),
            "n_matches_in_profile": home.get("n_matches_in_profile"),
            "style_label": home.get("style_label"),
            "cluster_label": home.get("cluster_label"),
            "overall_completion_rate": home.get("overall_completion_rate"),
            "overall_forward_ratio": home.get("overall_forward_ratio"),
            "overall_pass_length": home.get("overall_pass_length"),
            "dominant_zones": home.get("dominant_zones"),
        },
        "team_b": {
            "team": away_team,
            "season_name": away.get("season_name"),
            "competition_name": away.get("competition_name"),
            "n_matches_in_profile": away.get("n_matches_in_profile"),
            "style_label": away.get("style_label"),
            "cluster_label": away.get("cluster_label"),
            "overall_completion_rate": away.get("overall_completion_rate"),
            "overall_forward_ratio": away.get("overall_forward_ratio"),
            "overall_pass_length": away.get("overall_pass_length"),
            "dominant_zones": away.get("dominant_zones"),
        },
        "style_similarity": style_similarity,
        "matchup_type": matchup_type,
    }


def _source_coverage(*, fallback_used: bool) -> dict:
    used_sources = ["whoscored", "statsbomb"]
    if fallback_used:
        used_sources.append("tactical_profile_csv")
    return source_coverage_metadata(
        intent=IntentClass.TACTICAL_QUERY.value,
        used_sources=used_sources,
        required_sources=[
            "understat",
            "sofascore",
            "whoscored",
            "football_data",
            "native_stats_api",
            "statsbomb",
        ],
    )


class TacticalHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        requested_season = parsed_query.season or _latest_requested_season()

        def _finalize(engine_data: dict, *, fallback_used: bool) -> QueryPayload:
            if "cluster_label" not in engine_data:
                style_label = engine_data.get("style_label")
                if isinstance(style_label, str) and style_label:
                    engine_data["cluster_label"] = style_label

            if engine_data.get("query_type") == "single":
                prof = engine_data.get("profile_season") or engine_data.get("season_name")
                note = _fallback_note(requested_season, prof)
                if note:
                    engine_data["coverage_note"] = note

            if engine_data.get("query_type") == "comparison":
                home_prof = engine_data.get("profile_season_home")
                away_prof = engine_data.get("profile_season_away")
                if not _season_matches_requested(home_prof, requested_season) or not _season_matches_requested(away_prof, requested_season):
                    if home_prof and away_prof and home_prof == away_prof:
                        note = _fallback_note(requested_season, home_prof)
                    else:
                        note = (
                            f"{_season_display(requested_season)} tactical data not available for one or both teams; "
                            "using latest available seasons instead."
                        )
                    if note:
                        engine_data["coverage_note"] = note

            if fallback_used:
                engine_data["fallback_policy"] = (
                    "Model-based tactical inference unavailable; returned deterministic "
                    "team season profile fallback from tactical CSV features."
                )

            engine_data["source_coverage"] = _source_coverage(fallback_used=fallback_used)

            return QueryPayload(
                intent=IntentClass.TACTICAL_QUERY,
                engine_data=engine_data,
                partial=False,
                error=None,
            )

        try:
            from apps.predictions.ml.models.tactical.predict import TacticalAnalyser

            analyser = TacticalAnalyser()

            if parsed_query.home_team and parsed_query.away_team:
                result = analyser.compare_teams(
                    parsed_query.home_team, parsed_query.away_team, requested_season
                )
                if result is None:
                    result = _fallback_compare_profiles(
                        parsed_query.home_team,
                        parsed_query.away_team,
                        requested_season,
                    )
                    if result is None:
                        return QueryPayload(
                            intent=IntentClass.TACTICAL_QUERY,
                            engine_data={
                                "query_type": "comparison",
                                "home_team": parsed_query.home_team,
                                "away_team": parsed_query.away_team,
                                "requested_season": requested_season,
                                "source_coverage": _source_coverage(fallback_used=False),
                            },
                            partial=True,
                            error=f"No tactical profile found for one or both teams: "
                                  f"{parsed_query.home_team}, {parsed_query.away_team}.",
                        )
                engine_data = {
                    "query_type": "comparison",
                    "home_team": parsed_query.home_team,
                    "away_team": parsed_query.away_team,
                    "requested_season": requested_season,
                    "profile_season_home": result.get("team_a", {}).get("season_name"),
                    "profile_season_away": result.get("team_b", {}).get("season_name"),
                    **result,
                }
                return _finalize(engine_data, fallback_used=False)
            else:
                team = parsed_query.team or parsed_query.home_team
                if team is None:
                    return QueryPayload(
                        intent=IntentClass.TACTICAL_QUERY,
                        engine_data={},
                        partial=True,
                        error="No team specified for tactical query.",
                    )
                result = analyser.analyse_team(team, requested_season)
                if result is None:
                    fallback = _fallback_single_profile(team, requested_season)
                    if fallback is None:
                        return QueryPayload(
                            intent=IntentClass.TACTICAL_QUERY,
                            engine_data={
                                "query_type": "single",
                                "team": team,
                                "requested_season": requested_season,
                                "source_coverage": _source_coverage(fallback_used=False),
                            },
                            partial=True,
                            error=f"No tactical profile found for '{team}'.",
                        )
                    return _finalize(fallback, fallback_used=True)
                engine_data = {
                    "query_type": "single",
                    "team": team,
                    "requested_season": requested_season,
                    "profile_season": result.get("season_name"),
                    **result,
                }
                return _finalize(engine_data, fallback_used=False)
        except FileNotFoundError:
            team = parsed_query.team or parsed_query.home_team
            if parsed_query.home_team and parsed_query.away_team:
                fallback = _fallback_compare_profiles(
                    parsed_query.home_team,
                    parsed_query.away_team,
                    requested_season,
                )
                if fallback is not None:
                    return _finalize(fallback, fallback_used=True)
            elif team:
                fallback = _fallback_single_profile(team, requested_season)
                if fallback is not None:
                    return _finalize(fallback, fallback_used=True)

            return QueryPayload(
                intent=IntentClass.TACTICAL_QUERY,
                engine_data={
                    "query_type": "comparison" if parsed_query.home_team and parsed_query.away_team else "single",
                    "team": team,
                    "home_team": parsed_query.home_team,
                    "away_team": parsed_query.away_team,
                    "requested_season": requested_season,
                    "source_coverage": _source_coverage(fallback_used=False),
                },
                partial=True,
                error="Tactical model not available.",
            )
        except ValueError as exc:
            team = parsed_query.team or parsed_query.home_team
            if parsed_query.home_team and parsed_query.away_team:
                fallback = _fallback_compare_profiles(
                    parsed_query.home_team,
                    parsed_query.away_team,
                    requested_season,
                )
                if fallback is not None:
                    return _finalize(fallback, fallback_used=True)
            elif team:
                fallback = _fallback_single_profile(team, requested_season)
                if fallback is not None:
                    return _finalize(fallback, fallback_used=True)

            return QueryPayload(
                intent=IntentClass.TACTICAL_QUERY,
                engine_data={
                    "query_type": "comparison" if parsed_query.home_team and parsed_query.away_team else "single",
                    "team": team,
                    "home_team": parsed_query.home_team,
                    "away_team": parsed_query.away_team,
                    "requested_season": requested_season,
                    "source_coverage": _source_coverage(fallback_used=False),
                },
                partial=True,
                error=str(exc),
            )
        except Exception as exc:
            _logger.exception("TacticalHandler failed: %s", exc)
            team = parsed_query.team or parsed_query.home_team
            if parsed_query.home_team and parsed_query.away_team:
                fallback = _fallback_compare_profiles(
                    parsed_query.home_team,
                    parsed_query.away_team,
                    requested_season,
                )
                if fallback is not None:
                    return _finalize(fallback, fallback_used=True)
            elif team:
                fallback = _fallback_single_profile(team, requested_season)
                if fallback is not None:
                    return _finalize(fallback, fallback_used=True)

            return QueryPayload(
                intent=IntentClass.TACTICAL_QUERY,
                engine_data={
                    "query_type": "comparison" if parsed_query.home_team and parsed_query.away_team else "single",
                    "team": team,
                    "home_team": parsed_query.home_team,
                    "away_team": parsed_query.away_team,
                    "requested_season": requested_season,
                    "source_coverage": _source_coverage(fallback_used=False),
                },
                partial=True,
                error=str(exc),
            )