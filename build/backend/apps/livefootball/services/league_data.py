from __future__ import annotations

from typing import Any

import pandas as pd
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Count

from apps.livefootball.models import (
    Competition,
    CompetitionTableSnapshot,
    SavedLeagueScenario,
    SavedLeagueScenarioLockedFixture,
    TeamDirectoryEntry,
)
from apps.livefootball.services.simulation import (
    SUPPORTED_SIMULATION_MODES,
    simulate_league_scenario,
    simulate_league_season,
)
from apps.livefootball.services.team_bridge import (
    TeamMappingNotFoundError,
    get_competition_team_bridge,
    get_understat_league_code,
)
from apps.predictions.interpretations.league_commentary import (
    generate_comparison_commentary,
    generate_expected_table_commentary,
)
from apps.predictions.models import SimulationResult
from services.livefootball.helpers import shape_competition_item
from services.livefootball.queries import get_competition_table


RELEASE_ONE_COMPETITION_CODES = ("PL", "PD", "BL1", "SA", "FL1")
DEFAULT_MODE = "current_expected"


SIMULATION_MODE_ORDER = ["current_expected", "pre_season", "as_of_matchweek"]

def _get_competition(competition_id: int) -> Competition:
    return Competition.objects.get(pk=competition_id)


def _resolve_season_label(competition: Competition, season_label: str | None) -> str:
    resolved = (season_label or competition.current_season_label or "").strip()
    if not resolved:
        raise ValueError("season is required.")
    return resolved


def _competition_supported_modes(
    competition: Competition,
    season_label: str | None = None,
) -> tuple[list[str], list[dict[str, str]]]:
    try:
        get_understat_league_code(competition)
    except ValueError:
        unavailable = [
            {
                "mode": mode,
                "reason": "This competition is not mapped to an Understat-backed simulation league.",
            }
            for mode in SIMULATION_MODE_ORDER
        ]
        return [], unavailable

    return list(SIMULATION_MODE_ORDER), []

def _build_team_reference(entry: TeamDirectoryEntry | None, fallback_name: str) -> dict[str, Any]:
    if entry is None:
        return {
            "id": None,
            "external_id": "",
            "name": fallback_name,
            "short_name": "",
            "tla": "",
            "emblem_url": "",
        }

    return {
        "id": entry.id,
        "external_id": entry.external_id or "",
        "name": entry.name or fallback_name,
        "short_name": entry.short_name or "",
        "tla": entry.tla or "",
        "emblem_url": entry.emblem_url or "",
    }


def _build_canonical_team_directory(
    competition: Competition,
    season_label: str,
) -> dict[str, TeamDirectoryEntry]:
    mapping = get_competition_team_bridge(competition, season_label=season_label)
    team_entries = TeamDirectoryEntry.objects.filter(
        competition=competition,
        season_label=season_label,
        id__in=list(mapping.keys()),
    )

    by_canonical: dict[str, TeamDirectoryEntry] = {}
    for entry in team_entries:
        canonical_name = mapping.get(entry.id)
        if canonical_name:
            by_canonical[canonical_name] = entry

    return by_canonical


def _shape_expected_row(
    raw_row: dict[str, Any],
    canonical_team_directory: dict[str, TeamDirectoryEntry],
) -> dict[str, Any]:
    canonical_name = str(raw_row.get("team") or "").strip()
    entry = canonical_team_directory.get(canonical_name)

    return {
        "team": _build_team_reference(entry, canonical_name),
        "canonical_team_name": canonical_name,
        "predicted_points": float(raw_row.get("predicted_points") or 0.0),
        "predicted_position": int(raw_row.get("predicted_position") or 0),
        "position_probabilities": {
            int(position): float(probability)
            for position, probability in (raw_row.get("position_probabilities") or {}).items()
        },
        "title_probability": float(raw_row.get("title_probability") or 0.0),
        "top_4_probability": float(raw_row.get("top_4_probability") or 0.0),
        "relegation_probability": float(raw_row.get("relegation_probability") or 0.0),
        "simulated_wins": float(raw_row.get("simulated_wins") or 0.0),
        "simulated_draws": float(raw_row.get("simulated_draws") or 0.0),
        "simulated_losses": float(raw_row.get("simulated_losses") or 0.0),
        "simulated_goals_for": float(raw_row.get("simulated_goals_for") or 0.0),
        "simulated_goals_against": float(raw_row.get("simulated_goals_against") or 0.0),
    }

def _shape_scenario_fixture_row(
    raw_row: dict[str, Any],
    canonical_team_directory: dict[str, TeamDirectoryEntry],
) -> dict[str, Any]:
    home_canonical_name = str(raw_row.get("home_team") or "").strip()
    away_canonical_name = str(raw_row.get("away_team") or "").strip()

    home_entry = canonical_team_directory.get(home_canonical_name)
    away_entry = canonical_team_directory.get(away_canonical_name)

    return {
        "fixture_key": str(raw_row.get("fixture_key") or "").strip(),
        "home_team": _build_team_reference(home_entry, home_canonical_name),
        "away_team": _build_team_reference(away_entry, away_canonical_name),
    }


def _shape_locked_result_row(
    raw_row: dict[str, Any],
    canonical_team_directory: dict[str, TeamDirectoryEntry],
) -> dict[str, Any]:
    home_canonical_name = str(raw_row.get("home_team") or "").strip()
    away_canonical_name = str(raw_row.get("away_team") or "").strip()

    home_entry = canonical_team_directory.get(home_canonical_name)
    away_entry = canonical_team_directory.get(away_canonical_name)

    return {
        "fixture_key": str(raw_row.get("fixture_key") or "").strip(),
        "home_team": _build_team_reference(home_entry, home_canonical_name),
        "away_team": _build_team_reference(away_entry, away_canonical_name),
        "home_goals": int(raw_row.get("home_goals") or 0),
        "away_goals": int(raw_row.get("away_goals") or 0),
    }

def get_leagues_meta_payload() -> dict[str, Any]:
    competitions = (
        Competition.objects.filter(code__in=RELEASE_ONE_COMPETITION_CODES)
        .order_by("name", "id")
    )

    leagues: list[dict[str, Any]] = []

    for competition in competitions:
        season_labels = list(
            CompetitionTableSnapshot.objects.filter(competition=competition)
            .order_by("-season_label")
            .values_list("season_label", flat=True)
            .distinct()
        )
        supported_modes, unavailable_modes = _competition_supported_modes(competition)

        leagues.append(
            {
                "id": competition.id,
                "code": competition.code or "",
                "name": competition.name or "",
                "emblem_url": competition.emblem_url or "",
                "current_season_label": competition.current_season_label or "",
                "available_seasons": season_labels,
                "supported_modes": supported_modes,
                "unavailable_modes": unavailable_modes,
            }
        )

    return {"leagues": leagues}


def get_league_expected_table_payload(
    competition_id: int,
    *,
    season_label: str | None,
    mode: str | None,
    matchweek: int | None = None,
    projection_window: str | None = None,
) -> dict[str, Any]:
    competition = _get_competition(competition_id)
    resolved_season = _resolve_season_label(competition, season_label)
    resolved_mode = (mode or DEFAULT_MODE).strip()

    supported_modes, unavailable_modes = _competition_supported_modes(
        competition,
        season_label=resolved_season,
    )
    if resolved_mode not in supported_modes:
        if resolved_mode in {item["mode"] for item in unavailable_modes}:
            reason = next(
                item["reason"] for item in unavailable_modes if item["mode"] == resolved_mode
            )
            raise ValueError(reason)
        raise ValueError(
            f"Unsupported mode '{resolved_mode}'. Supported modes: {supported_modes}."
        )

    actual_table_payload = get_competition_table(
        competition_id=competition.id,
        season_label=resolved_season,
    )
    if not actual_table_payload["rows"]:
        raise ValueError(
            f"No actual table snapshot is available for competition {competition.id} in season '{resolved_season}'."
        )

    understat_league = get_understat_league_code(competition)
    canonical_team_directory = _build_canonical_team_directory(competition, resolved_season)

    simulation_kwargs: dict[str, Any] = {
        "league": understat_league,
        "season": resolved_season,
        "mode": resolved_mode,
        "matchweek": matchweek,
    }
    if projection_window:
        simulation_kwargs["projection_window"] = projection_window

    simulation_result = simulate_league_season(**simulation_kwargs)

    if simulation_result.get("data_cutoff_date"):
        SimulationResult.objects.update_or_create(
            league=understat_league,
            season=resolved_season,
            freeze_date=simulation_result["data_cutoff_date"],
            defaults={
                "results": simulation_result["expected_table"],
                "n_simulations": simulation_result.get("simulation_count", 0),
            },
        )

    expected_rows = [
        _shape_expected_row(row, canonical_team_directory)
        for row in simulation_result["expected_table"]
    ]

    commentary = generate_expected_table_commentary(
        expected_rows,
        competition.name,
        resolved_season,
        resolved_mode,
        simulation_result.get("simulation_count"),
        simulation_result.get("based_on_matchweek"),
        simulation_result.get("metadata", {}).get("remaining_fixtures"),
    )

    return {
        "competition": shape_competition_item(competition),
        "season_label": resolved_season,
        "mode": resolved_mode,
        "expected_table": expected_rows,
        "commentary": commentary,
        "metadata": {
            "supported_modes": supported_modes,
            "unavailable_modes": unavailable_modes,
            "based_on_matchweek": simulation_result.get("based_on_matchweek"),
            "data_cutoff_date": simulation_result.get("data_cutoff_date"),
            "simulation_count": simulation_result.get("simulation_count"),
            "engine_versions": simulation_result.get("metadata", {}).get("engine_versions", {}),
            "remaining_fixtures": simulation_result.get("metadata", {}).get("remaining_fixtures"),
            "remaining_fixtures_source": simulation_result.get("metadata", {}).get("remaining_fixtures_source"),
            "total_fixtures_simulated": simulation_result.get("metadata", {}).get("total_fixtures_simulated"),
            "total_matchweeks": simulation_result.get("metadata", {}).get("total_matchweeks"),
            "projection_window": simulation_result.get("metadata", {}).get("projection_window", "full_season"),
            "actual_table_source": "football-data table snapshots",
            "expected_table_source": "understat-backed simulation service",
        },
    }


def _actual_rows_by_canonical_name(
    actual_rows: list[dict[str, Any]],
    competition_team_bridge: dict[int, str],
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}

    for row in actual_rows:
        team_data = row.get("team") or {}
        team_id = team_data.get("id")
        if team_id is None:
            continue

        canonical_name = competition_team_bridge.get(team_id)
        if canonical_name:
            rows[canonical_name] = row

    return rows


def _expected_rows_by_canonical_name(
    expected_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}

    for row in expected_rows:
        canonical_name = str(row.get("canonical_team_name") or "").strip()
        if canonical_name:
            rows[canonical_name] = row

    return rows


def _build_deltas(
    actual_rows: list[dict[str, Any]],
    expected_rows: list[dict[str, Any]],
    competition_team_bridge: dict[int, str],
) -> list[dict[str, Any]]:
    actual_by_canonical = _actual_rows_by_canonical_name(actual_rows, competition_team_bridge)
    expected_by_canonical = _expected_rows_by_canonical_name(expected_rows)

    shared_teams = sorted(set(actual_by_canonical.keys()) & set(expected_by_canonical.keys()))
    deltas: list[dict[str, Any]] = []

    for canonical_name in shared_teams:
        actual_row = actual_by_canonical[canonical_name]
        expected_row = expected_by_canonical[canonical_name]

        actual_position = int(actual_row["position"])
        expected_position = int(expected_row["predicted_position"])
        actual_points = float(actual_row["points"])
        expected_points = float(expected_row["predicted_points"])

        deltas.append(
            {
                "team": expected_row["team"],
                "canonical_team_name": canonical_name,
                "actual_position": actual_position,
                "expected_position": expected_position,
                "position_delta": actual_position - expected_position,
                "actual_points": actual_points,
                "expected_points": expected_points,
                "points_delta": round(actual_points - expected_points, 2),
            }
        )

    deltas.sort(
        key=lambda item: (
            abs(item["position_delta"]),
            abs(item["points_delta"]),
            item["team"]["name"],
        ),
        reverse=True,
    )
    return deltas


def _compute_comparison_metrics(deltas: list[dict[str, Any]]) -> dict[str, Any]:
    if not deltas:
        return {
            "matched_team_count": 0,
            "average_absolute_position_delta": None,
            "average_absolute_points_delta": None,
            "points_correlation": None,
        }

    position_abs = [abs(item["position_delta"]) for item in deltas]
    points_abs = [abs(float(item["points_delta"])) for item in deltas]

    if len(deltas) >= 2:
        actual_points = pd.Series([float(item["actual_points"]) for item in deltas], dtype=float)
        expected_points = pd.Series([float(item["expected_points"]) for item in deltas], dtype=float)
        correlation = actual_points.corr(expected_points)
        points_correlation = None if pd.isna(correlation) else round(float(correlation), 4)
    else:
        points_correlation = None

    return {
        "matched_team_count": len(deltas),
        "average_absolute_position_delta": round(sum(position_abs) / len(position_abs), 2),
        "average_absolute_points_delta": round(sum(points_abs) / len(points_abs), 2),
        "points_correlation": points_correlation,
    }


def get_league_compare_payload(
    competition_id: int,
    *,
    season_label: str | None,
    mode: str | None,
    matchweek: int | None = None,
    projection_window: str | None = None,
) -> dict[str, Any]:
    competition = _get_competition(competition_id)
    resolved_season = _resolve_season_label(competition, season_label)

    snapshot_label: str | None = None
    if (mode or DEFAULT_MODE).strip() == "as_of_matchweek" and matchweek is not None:
        historical_snapshot = (
            CompetitionTableSnapshot.objects.filter(
                competition=competition,
                season_label=resolved_season,
                matchday__isnull=False,
                matchday__lte=matchweek,
            )
            .order_by("-matchday", "-synced_at", "-id")
            .first()
        )
        if historical_snapshot is not None:
            snapshot_label = historical_snapshot.snapshot_label

    actual_table_payload = get_competition_table(
        competition_id=competition.id,
        season_label=resolved_season,
        snapshot_label=snapshot_label,
    )
    if not actual_table_payload["rows"]:
        raise ValueError(
            f"No actual table snapshot is available for competition {competition.id} in season '{resolved_season}'."
        )

    expected_payload = get_league_expected_table_payload(
        competition_id=competition.id,
        season_label=resolved_season,
        mode=mode,
        matchweek=matchweek,
        projection_window=projection_window,
    )

    competition_team_bridge = get_competition_team_bridge(
        competition,
        season_label=resolved_season,
    )

    deltas = _build_deltas(
        actual_rows=actual_table_payload["rows"],
        expected_rows=expected_payload["expected_table"],
        competition_team_bridge=competition_team_bridge,
    )
    comparison_metrics = _compute_comparison_metrics(deltas)

    commentary = generate_comparison_commentary(
        actual_table_payload["rows"],
        expected_payload["expected_table"],
        competition.name,
        resolved_season,
        expected_payload["mode"],
        expected_payload["metadata"].get("remaining_fixtures"),
    )

    return {
        "competition": shape_competition_item(competition),
        "season_label": resolved_season,
        "mode": expected_payload["mode"],
        "actual_table": actual_table_payload["rows"],
        "expected_table": expected_payload["expected_table"],
        "deltas": deltas,
        "comparison_metrics": comparison_metrics,
        "commentary": commentary,
        "metadata": {
            **expected_payload["metadata"],
            "actual_snapshot_label": actual_table_payload.get("snapshot_label"),
            "actual_matchday": actual_table_payload.get("matchday"),
            "actual_synced_at": actual_table_payload.get("synced_at"),
        },
    }

def get_league_scenario_payload(
    competition_id: int,
    *,
    season_label: str | None,
    mode: str | None,
    matchweek: int | None = None,
    locked_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    competition = _get_competition(competition_id)
    resolved_season = _resolve_season_label(competition, season_label)
    resolved_mode = (mode or DEFAULT_MODE).strip()

    supported_modes, unavailable_modes = _competition_supported_modes(
        competition,
        season_label=resolved_season,
    )
    if resolved_mode not in supported_modes:
        if resolved_mode in {item["mode"] for item in unavailable_modes}:
            reason = next(
                item["reason"] for item in unavailable_modes if item["mode"] == resolved_mode
            )
            raise ValueError(reason)
        raise ValueError(
            f"Unsupported mode '{resolved_mode}'. Supported modes: {supported_modes}."
        )

    understat_league = get_understat_league_code(competition)
    canonical_team_directory = _build_canonical_team_directory(competition, resolved_season)

    simulation_result = simulate_league_scenario(
        league=understat_league,
        season=resolved_season,
        mode=resolved_mode,
        matchweek=matchweek,
        locked_results=locked_results or [],
    )

    expected_rows = [
        _shape_expected_row(row, canonical_team_directory)
        for row in simulation_result["expected_table"]
    ]
    scenario_fixtures = [
        _shape_scenario_fixture_row(row, canonical_team_directory)
        for row in simulation_result["remaining_fixtures"]
    ]
    shaped_locked_results = [
        _shape_locked_result_row(row, canonical_team_directory)
        for row in simulation_result["locked_results"]
    ]
    commentary = generate_expected_table_commentary(
        expected_rows,
        competition.name,
        resolved_season,
        resolved_mode,
        simulation_result.get("simulation_count"),
        simulation_result.get("based_on_matchweek"),
        simulation_result.get("metadata", {}).get("remaining_fixtures"),
    )

    return {
        "competition": shape_competition_item(competition),
        "season_label": resolved_season,
        "mode": resolved_mode,
        "remaining_fixtures": scenario_fixtures,
        "locked_results": shaped_locked_results,
        "expected_table": expected_rows,
        "commentary": commentary,
        "metadata": {
            "supported_modes": supported_modes,
            "unavailable_modes": unavailable_modes,
            "based_on_matchweek": simulation_result.get("based_on_matchweek"),
            "data_cutoff_date": simulation_result.get("data_cutoff_date"),
            "simulation_count": simulation_result.get("simulation_count"),
            "engine_versions": simulation_result.get("metadata", {}).get("engine_versions", {}),
            "remaining_fixtures": simulation_result.get("metadata", {}).get("remaining_fixtures"),
            "remaining_fixtures_source": simulation_result.get("metadata", {}).get("remaining_fixtures_source"),
            "remaining_fixtures_before_lock": simulation_result.get("metadata", {}).get(
                "remaining_fixtures_before_lock"
            ),
            "remaining_fixtures_after_lock": simulation_result.get("metadata", {}).get(
                "remaining_fixtures_after_lock"
            ),
            "total_fixtures_simulated": simulation_result.get("metadata", {}).get(
                "total_fixtures_simulated"
            ),
            "total_matchweeks": simulation_result.get("metadata", {}).get("total_matchweeks"),
            "actual_table_source": "football-data table snapshots",
            "expected_table_source": "understat-backed simulation service with locked results",
        },
    }

def list_saved_league_scenarios(
    user,
    *,
    competition_id: int,
    season_label: str | None = None,
    mode: str | None = None,
    based_on_matchweek: int | None = None,
) -> dict[str, Any]:
    queryset = (
        SavedLeagueScenario.objects.filter(
            user=user,
            competition_id=competition_id,
        )
        .select_related("competition")
        .annotate(locked_result_count=Count("locked_fixtures"))
        .order_by("-updated_at", "-id")
    )

    if season_label:
        queryset = queryset.filter(season_label=season_label.strip())
    if mode:
        queryset = queryset.filter(mode=mode.strip())
    if based_on_matchweek is not None:
        queryset = queryset.filter(based_on_matchweek=based_on_matchweek)

    items = [_shape_saved_scenario_list_item(item) for item in queryset]
    return {
        "count": len(items),
        "items": items,
    }


def get_saved_league_scenario_detail(user, *, scenario_id: int) -> dict[str, Any]:
    scenario = (
        SavedLeagueScenario.objects.filter(user=user)
        .select_related("competition")
        .prefetch_related("locked_fixtures")
        .get(pk=scenario_id)
    )
    return _shape_saved_scenario_detail(scenario)


def create_saved_league_scenario(
    user,
    *,
    competition_id: int,
    season_label: str | None,
    mode: str | None,
    matchweek: int | None = None,
    title: str,
    description: str = "",
    locked_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    preview = get_league_scenario_payload(
        competition_id=competition_id,
        season_label=season_label,
        mode=mode,
        matchweek=matchweek,
        locked_results=locked_results or [],
    )

    competition = _get_competition(competition_id)

    with transaction.atomic():
        scenario = SavedLeagueScenario.objects.create(
            user=user,
            competition=competition,
            title=title.strip(),
            description=description.strip(),
            season_label=preview["season_label"],
            mode=preview["mode"],
            based_on_matchweek=preview["metadata"].get("based_on_matchweek"),
            metadata={
                "simulation_count": preview["metadata"].get("simulation_count"),
                "engine_versions": preview["metadata"].get("engine_versions", {}),
            },
        )

        SavedLeagueScenarioLockedFixture.objects.bulk_create(
            [
                SavedLeagueScenarioLockedFixture(
                    scenario=scenario,
                    fixture_key=item["fixture_key"],
                    home_team_name=item["home_team"]["name"],
                    away_team_name=item["away_team"]["name"],
                    home_goals=item["home_goals"],
                    away_goals=item["away_goals"],
                )
                for item in preview["locked_results"]
            ]
        )

    return get_saved_league_scenario_detail(user, scenario_id=scenario.id)


def delete_saved_league_scenario(user, *, scenario_id: int) -> None:
    scenario = SavedLeagueScenario.objects.filter(user=user).get(pk=scenario_id)
    scenario.delete()
    
def _shape_saved_scenario_list_item(scenario: SavedLeagueScenario) -> dict[str, Any]:
    return {
        "id": scenario.id,
        "competition_id": scenario.competition_id,
        "competition_name": scenario.competition.name,
        "title": scenario.title,
        "description": scenario.description,
        "season_label": scenario.season_label,
        "mode": scenario.mode,
        "based_on_matchweek": scenario.based_on_matchweek,
        "locked_result_count": getattr(scenario, "locked_result_count", scenario.locked_fixtures.count()),
        "updated_at": scenario.updated_at,
    }


def _shape_saved_scenario_detail(
    scenario: SavedLeagueScenario,
) -> dict[str, Any]:
    return {
        "id": scenario.id,
        "competition": shape_competition_item(scenario.competition),
        "title": scenario.title,
        "description": scenario.description,
        "season_label": scenario.season_label,
        "mode": scenario.mode,
        "based_on_matchweek": scenario.based_on_matchweek,
        "locked_results": [
            {
                "id": fixture.id,
                "fixture_key": fixture.fixture_key,
                "home_team_name": fixture.home_team_name,
                "away_team_name": fixture.away_team_name,
                "home_goals": fixture.home_goals,
                "away_goals": fixture.away_goals,
            }
            for fixture in scenario.locked_fixtures.all().order_by("id")
        ],
        "created_at": scenario.created_at,
        "updated_at": scenario.updated_at,
    }