from __future__ import annotations

from typing import Any, Literal, TypedDict

from .templates import (
    comparison_alignment,
    comparison_full_alignment,
    comparison_generic_caveat,
    comparison_headline,
    comparison_mode_caveat,
    comparison_points_gap,
    comparison_underperformer,
    expected_accuracy_caveat,
    expected_confident_team,
    expected_mode_caveat,
    expected_relegation_warning,
    expected_settled_title_headline,
    expected_title_headline,
    expected_title_race,
    expected_uncertain_team,
)


CommentaryType = Literal["headline", "observation", "comparison", "caveat"]
ConfidenceLevel = Literal["high", "medium", "low"]


class CommentaryBlock(TypedDict):
    type: CommentaryType
    text: str
    confidence: ConfidenceLevel
    related_teams: list[str]


def _block(
    block_type: CommentaryType,
    text: str,
    confidence: ConfidenceLevel,
    related_teams: list[str] | None = None,
) -> CommentaryBlock:
    return {
        "type": block_type,
        "text": text,
        "confidence": confidence,
        "related_teams": related_teams or [],
    }


def _team_name_from_value(value: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        if isinstance(value.get("name"), str):
            return value["name"]
        team_value = value.get("team")
        if isinstance(team_value, dict) and isinstance(team_value.get("name"), str):
            return team_value["name"]
        if isinstance(team_value, str):
            return team_value

    return ""


def _expected_team_name(row: dict[str, Any]) -> str:
    return _team_name_from_value(row.get("team")) or _team_name_from_value(row)


def _actual_team_name(row: dict[str, Any]) -> str:
    return _team_name_from_value(row.get("team")) or _team_name_from_value(row)


def _predicted_position_confidence(row: dict[str, Any]) -> float:
    predicted_position = row.get("predicted_position")
    position_probabilities = row.get("position_probabilities") or {}

    if predicted_position is None:
        return 0.0

    if predicted_position in position_probabilities:
        return float(position_probabilities[predicted_position])

    as_string = str(predicted_position)
    if as_string in position_probabilities:
        return float(position_probabilities[as_string])

    return 0.0


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def generate_expected_table_commentary(
    expected_table: list[dict[str, Any]],
    league: str,
    season: str,
    mode: str,
    simulation_count: int | None = None,
    based_on_matchweek: int | None = None,
    remaining_fixtures: int | None = None,
) -> list[CommentaryBlock]:
    if not expected_table:
        return [
            _block(
                "headline",
                f"No expected table is available yet for {league} {season}.",
                "low",
                [],
            ),
            _block(
                "caveat",
                expected_mode_caveat(mode, based_on_matchweek, remaining_fixtures),
                "medium",
                [],
            ),
        ]

    rows = [row for row in expected_table if _expected_team_name(row)]
    if not rows:
        return [
            _block(
                "headline",
                f"No expected table is available yet for {league} {season}.",
                "low",
                [],
            )
        ]

    by_title = sorted(
        rows,
        key=lambda row: (
            -(_safe_float(row.get("title_probability")) or 0.0),
            -(_safe_float(row.get("predicted_points")) or 0.0),
            _expected_team_name(row),
        ),
    )
    leader = by_title[0]
    leader_name = _expected_team_name(leader)
    leader_title_prob = _safe_float(leader.get("title_probability")) or 0.0

    if remaining_fixtures == 0:
        return [
            _block(
                "headline",
                expected_settled_title_headline(leader_name, league),
                "high",
                [leader_name],
            ),
            _block(
                "caveat",
                expected_accuracy_caveat(simulation_count),
                "medium",
                [],
            ),
            _block(
                "caveat",
                expected_mode_caveat(mode, based_on_matchweek, remaining_fixtures),
                "medium",
                [],
            ),
        ]

    blocks: list[CommentaryBlock] = [
        _block(
            "headline",
            expected_title_headline(leader_name, league, leader_title_prob),
            "high" if leader_title_prob >= 0.5 else "medium",
            [leader_name],
        )
    ]

    confidence_ranked = sorted(
        rows,
        key=lambda row: (
            -_predicted_position_confidence(row),
            _expected_team_name(row),
        ),
    )
    most_certain = confidence_ranked[0]
    most_certain_name = _expected_team_name(most_certain)
    most_certain_position = int(most_certain.get("predicted_position") or 0)
    most_certain_confidence = _predicted_position_confidence(most_certain)

    if most_certain_position > 0:
        blocks.append(
            _block(
                "observation",
                expected_confident_team(
                    most_certain_name,
                    most_certain_position,
                    most_certain_confidence,
                ),
                "high" if most_certain_confidence >= 0.45 else "medium",
                [most_certain_name],
            )
        )

    least_certain = min(
        rows,
        key=lambda row: (
            _predicted_position_confidence(row),
            _expected_team_name(row),
        ),
    )
    least_certain_name = _expected_team_name(least_certain)
    least_certain_position = int(least_certain.get("predicted_position") or 0)
    least_certain_confidence = _predicted_position_confidence(least_certain)

    if least_certain_position > 0:
        blocks.append(
            _block(
                "observation",
                expected_uncertain_team(
                    least_certain_name,
                    least_certain_position,
                    least_certain_confidence,
                ),
                "medium" if least_certain_confidence >= 0.2 else "low",
                [least_certain_name],
            )
        )

    if len(by_title) >= 2 and leader_title_prob < 0.995:
        second = by_title[1]
        second_name = _expected_team_name(second)
        second_title_prob = _safe_float(second.get("title_probability")) or 0.0

        if second_title_prob >= 0.15:
            blocks.append(
                _block(
                    "observation",
                    expected_title_race(
                        leader_name,
                        leader_title_prob,
                        second_name,
                        second_title_prob,
                    ),
                    "medium",
                    [leader_name, second_name],
                )
            )

    relegation_ranked = sorted(
        rows,
        key=lambda row: (
            -(_safe_float(row.get("relegation_probability")) or 0.0),
            _expected_team_name(row),
        ),
    )
    relegation_candidate = relegation_ranked[0]
    relegation_team = _expected_team_name(relegation_candidate)
    relegation_prob = _safe_float(relegation_candidate.get("relegation_probability")) or 0.0

    if relegation_prob >= 0.3:
        blocks.append(
            _block(
                "observation",
                expected_relegation_warning(relegation_team, relegation_prob),
                "medium" if relegation_prob < 0.6 else "high",
                [relegation_team],
            )
        )

    blocks.append(
        _block(
            "caveat",
            expected_accuracy_caveat(simulation_count),
            "medium",
            [],
        )
    )
    blocks.append(
        _block(
            "caveat",
            expected_mode_caveat(mode, based_on_matchweek, remaining_fixtures),
            "medium",
            [],
        )
    )

    return blocks


def generate_comparison_commentary(
    actual_table: list[dict[str, Any]],
    expected_table: list[dict[str, Any]],
    league: str,
    season: str,
    mode: str,
    remaining_fixtures: int | None = None,
) -> list[CommentaryBlock]:
    if not actual_table or not expected_table:
        return [
            _block(
                "headline",
                f"No comparison commentary is available yet for {league} {season}.",
                "low",
                [],
            ),
            _block(
                "caveat",
                comparison_mode_caveat(mode, remaining_fixtures),
                "medium",
                [],
            ),
        ]

    expected_by_team = {
        _expected_team_name(row): row
        for row in expected_table
        if _expected_team_name(row)
    }
    actual_by_team = {
        _actual_team_name(row): row
        for row in actual_table
        if _actual_team_name(row)
    }

    shared_teams = sorted(set(expected_by_team.keys()) & set(actual_by_team.keys()))
    if not shared_teams:
        return [
            _block(
                "headline",
                f"No overlapping teams were available for comparison in {league} {season}.",
                "low",
                [],
            )
        ]

    deltas: list[dict[str, Any]] = []

    for team in shared_teams:
        actual_row = actual_by_team[team]
        expected_row = expected_by_team[team]

        actual_position = actual_row.get("position")
        expected_position = expected_row.get("predicted_position")

        if actual_position is None or expected_position is None:
            continue

        position_delta = int(actual_position) - int(expected_position)

        deltas.append(
            {
                "team": team,
                "actual_position": int(actual_position),
                "expected_position": int(expected_position),
                "position_delta": position_delta,
                "actual_points": _safe_float(actual_row.get("points")),
                "expected_points": _safe_float(expected_row.get("predicted_points")),
            }
        )

    if not deltas:
        return [
            _block(
                "headline",
                f"Comparison data was incomplete for {league} {season}.",
                "low",
                [],
            )
        ]

    max_abs_position_delta = max(abs(item["position_delta"]) for item in deltas)

    if remaining_fixtures == 0 and max_abs_position_delta == 0:
        blocks: list[CommentaryBlock] = [
            _block(
                "headline",
                comparison_full_alignment(),
                "high",
                [],
            )
        ]
    else:
        overperformer = min(
            deltas,
            key=lambda item: (item["position_delta"], item["team"]),
        )
        underperformer = max(
            deltas,
            key=lambda item: (item["position_delta"], item["team"]),
        )

        blocks = []

        if overperformer["position_delta"] < 0:
            blocks.append(
                _block(
                    "headline",
                    comparison_headline(
                        overperformer["team"],
                        overperformer["actual_position"],
                        overperformer["expected_position"],
                    ),
                    "high" if abs(overperformer["position_delta"]) >= 3 else "medium",
                    [overperformer["team"]],
                )
            )
        else:
            actual_leader = min(deltas, key=lambda item: (item["actual_position"], item["team"]))
            blocks.append(
                _block(
                    "headline",
                    comparison_alignment(actual_leader["team"]),
                    "medium",
                    [actual_leader["team"]],
                )
            )

        if underperformer["position_delta"] > 0:
            blocks.append(
                _block(
                    "comparison",
                    comparison_underperformer(
                        underperformer["team"],
                        underperformer["actual_position"],
                        underperformer["expected_position"],
                    ),
                    "high" if underperformer["position_delta"] >= 3 else "medium",
                    [underperformer["team"]],
                )
            )

    biggest_points_gap = max(
        deltas,
        key=lambda item: abs(
            (item["actual_points"] or 0.0) - (item["expected_points"] or 0.0)
        ),
    )

    if biggest_points_gap["actual_points"] is not None and biggest_points_gap["expected_points"] is not None:
        blocks.append(
            _block(
                "comparison",
                comparison_points_gap(
                    biggest_points_gap["team"],
                    biggest_points_gap["actual_points"],
                    biggest_points_gap["expected_points"],
                ),
                "medium",
                [biggest_points_gap["team"]],
            )
        )

    blocks.append(
        _block(
            "caveat",
            comparison_mode_caveat(mode, remaining_fixtures),
            "medium",
            [],
        )
    )
    blocks.append(
        _block(
            "caveat",
            comparison_generic_caveat(),
            "medium",
            [],
        )
    )

    return blocks