from __future__ import annotations

from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.livefootball.models import CompetitionTopScorer, PlayerDirectoryEntry
from apps.livefootball.services.native_stats import (
    NativeStatsError,
    build_minutes_lookup,
    get_default_all_time_streaks,
    get_homepage_latest_hat_tricks as get_native_stats_latest_hat_tricks,
    get_homepage_strikers_with_a_lull as get_native_stats_strikers_with_a_lull,
)
from services.livefootball.queries import (
    get_competition_previous_next_fixtures,
    get_competition_scorers,
    get_competition_table,
    list_competitions,
    list_team_players,
)

import re
import unicodedata

HOMEPAGE_LEAGUE_ORDER = [
    {
        "key": "PL",
        "code_aliases": ("PL",),
        "name_aliases": ("Premier League",),
    },
    {
        "key": "LL",
        "code_aliases": ("PD", "LL"),
        "name_aliases": ("La Liga", "Primera Division", "Primera División"),
    },
    {
        "key": "BL1",
        "code_aliases": ("BL1",),
        "name_aliases": ("Bundesliga",),
    },
    {
        "key": "SA",
        "code_aliases": ("SA",),
        "name_aliases": ("Serie A",),
    },
    {
        "key": "FL1",
        "code_aliases": ("FL1",),
        "name_aliases": ("Ligue 1",),
    },
    {
        "key": "RPL",
        "code_aliases": ("RPL",),
        "name_aliases": ("Russian Premier League",),
    },
]

ATTACKING_POSITION_TOKENS = {
    "ST",
    "CF",
    "FW",
    "FWD",
    "LW",
    "RW",
    "LF",
    "RF",
    "SS",
    "ATT",
    "ATTACKER",
    "FORWARD",
    "STRIKER",
    "CENTRE-FORWARD",
    "CENTER-FORWARD",
    "LEFT WINGER",
    "RIGHT WINGER",
}
GOALKEEPER_POSITION_TOKENS = {
    "GK",
    "GOALKEEPER",
}
FALLBACK_TOP_SCORERS_LIMIT = 10
MATCH_PREVIEW_LIMIT = 5
TOP_PERFORMING_TEAMS_LIMIT = 10
NATIVE_STATS_HAT_TRICKS_LIMIT = 8
NATIVE_STATS_LULL_LIMIT = 8

def _get_native_stats_from_snapshot(key: str, fallback):
    from apps.livefootball.models import NativeStatsSnapshot
    snapshot = NativeStatsSnapshot.objects.filter(
        surface_key=NativeStatsSnapshot.SURFACE_HOMEPAGE,
        is_active=True,
    ).first()
    if snapshot:
        return snapshot.payload.get(key, fallback)
    return fallback

def get_livefootball_homepage_payload() -> dict[str, Any]:
    use_snapshot = getattr(settings, 'USE_PUBLISHED_LIVEFOOTBALL_SNAPSHOT', False)

    if use_snapshot:
        latest_hat_tricks_data = _get_native_stats_from_snapshot('latest_hat_tricks', {'items': [], 'updated_at': None})
        strikers_with_a_lull_data = _get_native_stats_from_snapshot('strikers_with_a_lull', {'items': [], 'updated_at': None})
        all_time_streaks_data = _get_native_stats_from_snapshot('all_time_streaks', {'all_time': [], 'current': [], 'updated_at': None, 'cta': {}})
    else:
        latest_hat_tricks_data = get_homepage_latest_hat_tricks()
        strikers_with_a_lull_data = get_homepage_strikers_with_a_lull()
        all_time_streaks_data = get_homepage_all_time_streaks()

    return {
        "generated_at": timezone.now().isoformat(),
        "league_order": [item["key"] for item in HOMEPAGE_LEAGUE_ORDER],
        "league_snapshot": get_homepage_league_previews(),
        "top_performing_teams": get_homepage_top_performing_teams(),
        "top_performing_scorers": get_homepage_top_performing_scorers(),
        "latest_hat_tricks": latest_hat_tricks_data,
        "strikers_with_a_lull": strikers_with_a_lull_data,
        "recent_matches_by_league": get_homepage_recent_matches_by_league(),
        "upcoming_matches_by_league": get_homepage_upcoming_matches_by_league(),
        "first_vs_last_by_league": get_homepage_first_vs_last_by_league(),
        "all_time_streaks": all_time_streaks_data,
    }

def get_homepage_league_previews() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    for competition in get_homepage_competitions():
        table_payload = get_competition_table(competition["id"])
        rows = table_payload.get("rows", [])

        cards.append(
            {
                "competition": _shape_overview_competition_reference(
                    table_payload.get("competition", {})
                ),
                "synced_at": table_payload.get("synced_at"),
                "top_rows": [_shape_league_snapshot_row(row) for row in rows[:3]],
                "bottom_rows": [
                    _shape_league_snapshot_row(row)
                    for row in (rows[-3:] if len(rows) >= 3 else rows)
                ],
                "cta": _build_cta(
                    label="View league",
                    path="/livefootball/leagues",
                    query={"competition": competition.get("code", "")},
                ),
            }
        )

    return cards

def get_homepage_top_performing_scorers() -> dict[str, Any]:
    ranked_items: list[dict[str, Any]] = []
    updated_candidates: list[str] = []

    for competition in get_homepage_competitions():
        scorers_payload = get_competition_scorers(competition["id"], limit=3)

        raw_competition = scorers_payload.get("competition", {})
        competition_ref = _shape_overview_competition_reference(raw_competition)

        updated_at = raw_competition.get("last_synced_at")
        if updated_at:
            updated_candidates.append(updated_at)

        for item in scorers_payload.get("items", []):
            player_ref = _shape_scorer_player_reference(item)
            team_ref = _shape_overview_team_reference(item.get("team", {}))
            identity_key = _build_top_scorer_identity_key(item, team_ref)
            loose_identity_key = _build_top_scorer_loose_identity_key(
                item,
                player_ref,
                team_ref,
                competition_ref,
            )
            coarse_identity_key = _build_top_scorer_coarse_identity_key(
                item,
                player_ref,
                competition_ref,
            )
            ranked_items.append(
                {
                    "rank": item.get("rank"),
                    "player": player_ref,
                    "team": team_ref,
                    "competition": competition_ref,
                    "summary": _build_top_scorer_summary(item),
                    "metric_label": "Goals",
                    "metric_value": str(item.get("goals") or 0),
                    "sort_goals": item.get("goals") or 0,
                    "sort_penalties": item.get("penalties") or 0,
                    "sort_rank": item.get("rank") or 9999,
                    "sort_name": (player_ref.get("name") or "").lower(),
                    "identity_key": identity_key,
                    "loose_identity_key": loose_identity_key,
                    "coarse_identity_key": coarse_identity_key,
                    "cta": _build_cta(
                        label="View player",
                        path="/livefootball/players",
                        query={
                            "trend": "top-performing-scorers",
                            "playerId": _stringify_player_id(item),
                        },
                    ),
                }
            )

    deduped_by_identity: dict[str, dict[str, Any]] = {}
    deduped_by_loose_identity: dict[str, str] = {}
    deduped_by_coarse_identity: dict[str, str] = {}
    for item in ranked_items:
        identity_key = item.get("identity_key") or ""
        loose_identity_key = item.get("loose_identity_key") or ""
        coarse_identity_key = item.get("coarse_identity_key") or ""
        current = deduped_by_identity.get(identity_key)
        if current is not None:
            if _is_better_scorer_candidate(item, current):
                deduped_by_identity[identity_key] = item
            continue

        if loose_identity_key and loose_identity_key in deduped_by_loose_identity:
            mapped_identity_key = deduped_by_loose_identity[loose_identity_key]
            current = deduped_by_identity[mapped_identity_key]
            if _is_better_scorer_candidate(item, current):
                deduped_by_identity[mapped_identity_key] = item
            continue

        if coarse_identity_key and coarse_identity_key in deduped_by_coarse_identity:
            mapped_identity_key = deduped_by_coarse_identity[coarse_identity_key]
            current = deduped_by_identity[mapped_identity_key]
            if _is_better_scorer_candidate(item, current):
                deduped_by_identity[mapped_identity_key] = item
            continue

        deduped_by_identity[identity_key] = item
        if loose_identity_key:
            deduped_by_loose_identity[loose_identity_key] = identity_key
        if coarse_identity_key:
            deduped_by_coarse_identity[coarse_identity_key] = identity_key

    ranked_items = list(deduped_by_identity.values())

    ranked_items.sort(
        key=lambda item: (
            -item["sort_goals"],
            item["sort_penalties"],
            item["sort_rank"],
            item["sort_name"],
        )
    )

    items = []
    for display_rank, item in enumerate(ranked_items[:FALLBACK_TOP_SCORERS_LIMIT], start=1):
        items.append(
            {
                "rank": display_rank,
                "player": item["player"],
                "team": item["team"],
                "competition": item["competition"],
                "summary": item["summary"],
                "metric_label": item["metric_label"],
                "metric_value": item["metric_value"],
                "cta": item["cta"],
            }
        )

    return {
        "updated_at": max(updated_candidates) if updated_candidates else None,
        "items": items,
    }

def get_homepage_top_performing_teams() -> dict[str, Any]:
    ranked_items: list[dict[str, Any]] = []
    updated_candidates: list[str] = []

    for competition in get_homepage_competitions():
        table_payload = get_competition_table(competition["id"])
        competition_ref = _shape_overview_competition_reference(
            table_payload.get("competition", {})
        )
        synced_at = table_payload.get("synced_at")
        if synced_at:
            updated_candidates.append(synced_at)

        for row in table_payload.get("rows", []):
            played = row.get("played") or 0
            if played <= 0:
                continue

            points = row.get("points") or 0
            goals_for = row.get("goals_for") or 0
            goal_difference = row.get("goal_difference") or 0
            form_label = row.get("form") or ""

            points_per_game = round(points / played, 2)
            goals_for_per_game = round(goals_for / played, 2)
            goal_difference_per_game = round(goal_difference / played, 2)
            form_score = _form_points(form_label)

            team_ref = _shape_overview_team_reference(row.get("team", {}))

            ranked_items.append(
                {
                    "rank": None,
                    "team": team_ref,
                    "competition": competition_ref,
                    "summary": (
                        f"{points_per_game:.2f} points per game and "
                        f"{goals_for_per_game:.2f} goals per game."
                    ),
                    "metric_label": "PPG",
                    "metric_value": f"{points_per_game:.2f}",
                    "form_label": form_label,
                    "sort_points_per_game": points_per_game,
                    "sort_form_score": form_score,
                    "sort_goal_difference_per_game": goal_difference_per_game,
                    "sort_goals_for_per_game": goals_for_per_game,
                    "sort_points": points,
                    "sort_name": (team_ref.get("name") or "").lower(),
                    "cta": _build_cta(
                        label="View club",
                        path="/livefootball/clubs",
                        query={
                            "competition": competition.get("code", ""),
                            "teamId": team_ref.get("id"),
                        },
                    ),
                }
            )

    ranked_items.sort(
        key=lambda item: (
            -item["sort_points_per_game"],
            -item["sort_form_score"],
            -item["sort_goal_difference_per_game"],
            -item["sort_goals_for_per_game"],
            -item["sort_points"],
            item["sort_name"],
        )
    )

    items: list[dict[str, Any]] = []
    for display_rank, item in enumerate(ranked_items[:TOP_PERFORMING_TEAMS_LIMIT], start=1):
        items.append(
            {
                "rank": display_rank,
                "team": item["team"],
                "competition": item["competition"],
                "summary": item["summary"],
                "metric_label": item["metric_label"],
                "metric_value": item["metric_value"],
                "form_label": item.get("form_label") or "",
                "cta": item["cta"],
            }
        )

    return {
        "updated_at": max(updated_candidates) if updated_candidates else None,
        "items": items,
    }


def get_homepage_latest_hat_tricks() -> dict[str, Any]:
    try:
        rows = get_native_stats_latest_hat_tricks(limit=NATIVE_STATS_HAT_TRICKS_LIMIT)
    except NativeStatsError:
        rows = []

    items: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        scorer_name = row.get("scorer_name") or ""
        directory_entry = _resolve_directory_entry_by_name(scorer_name)

        player_ref = _shape_overview_player_reference_from_directory(
            directory_entry,
            fallback_name=scorer_name,
        )
        if directory_entry:
            team_ref = _shape_overview_team_reference_from_directory(directory_entry)
            competition_ref = _shape_overview_competition_reference_from_directory(directory_entry)
        else:
            team_ref = _shape_overview_team_reference(
                {
                    "id": None,
                    "name": row.get("team_name") or "Unknown club",
                    "short_name": None,
                    "crest_url": None,
                }
            )
            competition_ref = _shape_overview_competition_reference(
                {
                    "id": 0,
                    "code": row.get("competition_code") or None,
                    "name": row.get("competition_code") or "Live Football",
                    "country": None,
                    "emblem_url": None,
                }
            )

        items.append(
            {
                "rank": index,
                "player": player_ref,
                "team": team_ref,
                "competition": competition_ref,
                "summary": _build_hat_trick_summary(
                    date_value=row.get("date") or "",
                    match_label=row.get("match_label") or "",
                    result=row.get("result") or "",
                ),
                "metric_label": "Result",
                "metric_value": row.get("result") or "",
                "cta": _build_cta(
                    label="View player",
                    path="/livefootball/players",
                    query=_build_player_trend_query(
                        trend="latest-hat-tricks",
                        player_ref=player_ref,
                    ),
                ),
            }
        )

    return {
        "updated_at": timezone.now().isoformat() if items else None,
        "items": items,
    }


def get_homepage_strikers_with_a_lull() -> dict[str, Any]:
    try:
        rows = get_native_stats_strikers_with_a_lull(limit=NATIVE_STATS_LULL_LIMIT)
    except NativeStatsError:
        rows = []

    items: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        scorer_name = row.get("scorer_name") or ""
        directory_entry = _resolve_directory_entry_by_name(scorer_name)

        player_ref = _shape_overview_player_reference_from_directory(
            directory_entry,
            fallback_name=scorer_name,
        )
        if directory_entry:
            team_ref = _shape_overview_team_reference_from_directory(directory_entry)
            competition_ref = _shape_overview_competition_reference_from_directory(directory_entry)
        else:
            team_ref = _shape_overview_team_reference(
                {
                    "id": None,
                    "name": row.get("team_name") or "Unknown club",
                    "short_name": None,
                    "crest_url": None,
                }
            )
            competition_ref = _shape_overview_competition_reference(
                {
                    "id": 0,
                    "code": None,
                    "name": "Live Football",
                    "country": None,
                    "emblem_url": None,
                }
            )
        no_goal_matches = row.get("no_goal_matches")

        items.append(
            {
                "rank": index,
                "player": player_ref,
                "team": team_ref,
                "competition": competition_ref,
                "summary": _build_striker_lull_summary(
                    last_scored=row.get("last_scored") or "",
                    match_label=row.get("match_label") or "",
                    no_goal_matches=no_goal_matches,
                    result=row.get("result") or "",
                ),
                "metric_label": "Goals per game",
                "metric_value": _format_goals_per_game_metric(
                    row.get("goals_per_game"),
                    scorer_name=scorer_name,
                    directory_entry=directory_entry,
                ),
                "cta": _build_cta(
                    label="View player",
                    path="/livefootball/players",
                    query=_build_player_trend_query(
                        trend="strikers-with-a-lull",
                        player_ref=player_ref,
                    ),
                ),
            }
        )

    return {
        "updated_at": timezone.now().isoformat() if items else None,
        "items": items,
    }


def get_homepage_recent_matches_by_league() -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    for competition in get_homepage_competitions():
        fixtures_payload = get_competition_previous_next_fixtures(
            competition["id"],
            previous_limit=MATCH_PREVIEW_LIMIT,
            next_limit=MATCH_PREVIEW_LIMIT,
        )

        raw_competition = fixtures_payload.get("competition", {})
        competition_ref = _shape_overview_competition_reference(raw_competition)

        items = [
            _shape_match_preview_item(item)
            for item in fixtures_payload.get("previous", [])
        ]

        blocks.append(
            {
                "competition": competition_ref,
                "synced_at": raw_competition.get("last_synced_at"),
                "items": items,
                "cta": _build_cta(
                    label="View matches",
                    path="/livefootball/matches",
                    query={
                        "competition": competition.get("code", ""),
                        "tab": "recent",
                    },
                ),
            }
        )

    return blocks

def get_homepage_upcoming_matches_by_league() -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    for competition in get_homepage_competitions():
        fixtures_payload = get_competition_previous_next_fixtures(
            competition["id"],
            previous_limit=MATCH_PREVIEW_LIMIT,
            next_limit=MATCH_PREVIEW_LIMIT,
        )

        raw_competition = fixtures_payload.get("competition", {})
        competition_ref = _shape_overview_competition_reference(raw_competition)

        items = [
            _shape_match_preview_item(item)
            for item in fixtures_payload.get("next", [])
        ]

        blocks.append(
            {
                "competition": competition_ref,
                "synced_at": raw_competition.get("last_synced_at"),
                "items": items,
                "cta": _build_cta(
                    label="View matches",
                    path="/livefootball/matches",
                    query={
                        "competition": competition.get("code", ""),
                        "tab": "upcoming",
                    },
                ),
            }
        )

    return blocks

def get_homepage_first_vs_last_by_league() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    for competition in get_homepage_competitions():
        table_payload = get_competition_table(competition["id"])
        rows = table_payload.get("rows", [])

        competition_ref = _shape_overview_competition_reference(
            table_payload.get("competition", {})
        )

        if not rows:
            cards.append(
                {
                    "competition": competition_ref,
                    "synced_at": table_payload.get("synced_at"),
                    "leader": None,
                    "bottom": None,
                    "spotlight_players": [],
                    "cta": _build_cta(
                        label="View clubs",
                        path="/livefootball/clubs",
                        query={
                            "competition": competition.get("code", ""),
                            "mode": "first-v-last",
                        },
                    ),
                }
            )
            continue

        leader_row = rows[0]
        bottom_row = rows[-1]

        spotlight_players = _build_first_vs_last_spotlights(
            leader_team_id=_safe_nested_int(leader_row, "team", "id"),
            leader_team_name=_safe_nested_str(leader_row, "team", "name"),
            bottom_team_id=_safe_nested_int(bottom_row, "team", "id"),
            bottom_team_name=_safe_nested_str(bottom_row, "team", "name"),
        )

        cards.append(
            {
                "competition": competition_ref,
                "synced_at": table_payload.get("synced_at"),
                "leader": _shape_first_vs_last_table_row(leader_row),
                "bottom": _shape_first_vs_last_table_row(bottom_row),
                "spotlight_players": spotlight_players,
                "cta": _build_cta(
                    label="View clubs",
                    path="/livefootball/clubs",
                    query={
                        "competition": competition.get("code", ""),
                        "mode": "first-v-last",
                    },
                ),
            }
        )

    return cards

def get_homepage_all_time_streaks() -> dict[str, Any]:
    try:
        streak_rows = get_default_all_time_streaks(limit=8)
    except NativeStatsError:
        streak_rows = []

    items = []
    for row in streak_rows:
        items.append(
            {
                "competition_code": "",
                "competition_name": "",
                "team_name": row.get("team_name") or "",
                "team_id": None,
                "crest_url": None,
                "streak_value": row.get("matches"),
                "label": row.get("label") or "All-time streak",
                "summary": row.get("summary") or "",
            }
        )

    return {
        "updated_at": timezone.now().isoformat() if items else None,
        "all_time": items[:4],
        "current": [],
        "cta": _build_cta(
            label="View streaks",
            path="/livefootball/streaks",
            query={},
        ),
    }


def get_homepage_competitions() -> list[dict[str, Any]]:
    competitions = list_competitions()
    ordered: list[dict[str, Any]] = []

    for spec in HOMEPAGE_LEAGUE_ORDER:
        match = _find_competition_match(competitions, spec)
        if match:
            ordered.append(match)

    return ordered


def _find_competition_match(
    competitions: list[dict[str, Any]],
    spec: dict[str, Any],
) -> dict[str, Any] | None:
    code_aliases = {alias.strip().upper() for alias in spec.get("code_aliases", ()) if alias}
    name_aliases = {alias.strip().lower() for alias in spec.get("name_aliases", ()) if alias}

    for competition in competitions:
        code = (competition.get("code") or "").strip().upper()
        name = (competition.get("name") or "").strip().lower()

        if code and code in code_aliases:
            return competition

        if name and name in name_aliases:
            return competition

    return None


def _normalise_player_name_for_lookup(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _lookup_player_minutes(player: dict[str, Any]) -> int | None:
    team_external_id = (player.get("team") or {}).get("external_id")
    if not team_external_id:
        return None
    player_name = player.get("player_name") or ""
    if not player_name:
        return None
    try:
        lookup = build_minutes_lookup(team_external_id)
    except NativeStatsError:
        return None
    normalised = _normalise_player_name_for_lookup(player_name)
    match = lookup.get(normalised)
    return match["minutes_played"] if match else None


def _lookup_player_minutes_from_map(
    player: dict[str, Any],
    minutes_lookup: dict[str, dict[str, Any]],
) -> int | None:
    player_name = player.get("player_name") or ""
    if not player_name:
        return None
    normalised = _normalise_player_name_for_lookup(player_name)
    match = minutes_lookup.get(normalised)
    return match.get("minutes_played") if match else None


def _build_team_minutes_lookup(players: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    team_external_id = next(
        (
            (item.get("team") or {}).get("external_id")
            for item in players
            if (item.get("team") or {}).get("external_id")
        ),
        None,
    )
    if not team_external_id:
        return {}
    try:
        return build_minutes_lookup(team_external_id)
    except NativeStatsError:
        return {}


def _select_player_with_most_minutes(
    players: list[dict[str, Any]],
    target: str,
    minutes_lookup: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, int | None]:
    if target == "attacker":
        filtered = [item for item in players if _is_attacking_player(item)]
    elif target == "goalkeeper":
        filtered = [item for item in players if _is_goalkeeper(item)]
    else:
        filtered = []

    if not filtered:
        selected = _select_preferred_player(players, target=target)
        if not selected:
            return None, None
        return selected, _lookup_player_minutes_from_map(selected, minutes_lookup)

    ranked = sorted(
        filtered,
        key=lambda item: (
            -(_lookup_player_minutes_from_map(item, minutes_lookup) or -1),
            0 if item.get("squad_number") is not None else 1,
            item.get("squad_number") if item.get("squad_number") is not None else 999,
            (item.get("player_name") or "").lower(),
            item.get("id") or 0,
        ),
    )
    selected = ranked[0]
    return selected, _lookup_player_minutes_from_map(selected, minutes_lookup)


def _build_team_spotlights(team_id: int, team_name: str) -> list[dict[str, Any]]:
    payload = list_team_players(team_id, active_only=True)
    players = payload.get("items", [])
    if not players:
        return []

    minutes_lookup = _build_team_minutes_lookup(players)
    items: list[dict[str, Any]] = []

    attacker, attacker_minutes = _select_player_with_most_minutes(
        players,
        target="attacker",
        minutes_lookup=minutes_lookup,
    )
    if attacker:
        items.append(
            _shape_spotlight_player(
                team_id=team_id,
                team_name=team_name,
                player=attacker,
                reason_label="Highest-minutes attacker",
                minutes_played=attacker_minutes,
            )
        )

    goalkeeper, goalkeeper_minutes = _select_player_with_most_minutes(
        players,
        target="goalkeeper",
        minutes_lookup=minutes_lookup,
    )
    if goalkeeper:
        attacker_id = attacker.get("id") if attacker else None
        goalkeeper_id = goalkeeper.get("id")
        if attacker_id is None or goalkeeper_id != attacker_id:
            items.append(
                _shape_spotlight_player(
                    team_id=team_id,
                    team_name=team_name,
                    player=goalkeeper,
                    reason_label="Highest-minutes goalkeeper",
                    minutes_played=goalkeeper_minutes,
                )
            )

    return items


def _build_first_vs_last_spotlights(
    leader_team_id: int | None,
    leader_team_name: str,
    bottom_team_id: int | None,
    bottom_team_name: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    if leader_team_id:
        items.extend(_build_team_spotlights(leader_team_id, leader_team_name))

    if bottom_team_id:
        items.extend(_build_team_spotlights(bottom_team_id, bottom_team_name))

    return items

def _select_preferred_player(
    players: list[dict[str, Any]],
    target: str,
) -> dict[str, Any] | None:
    if not players:
        return None

    if target == "attacker":
        filtered = [item for item in players if _is_attacking_player(item)]
        if filtered:
            return _sort_players_for_selection(filtered)[0]

    if target == "goalkeeper":
        filtered = [item for item in players if _is_goalkeeper(item)]
        if filtered:
            return _sort_players_for_selection(filtered)[0]

    return _sort_players_for_selection(players)[0]


def _sort_players_for_selection(
    players: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        players,
        key=lambda item: (
            _player_position_priority(item),
            0 if item.get("squad_number") is not None else 1,
            item.get("squad_number") if item.get("squad_number") is not None else 999,
            (item.get("player_name") or "").lower(),
            item.get("id") or 0,
        ),
    )

def _player_position_priority(player: dict[str, Any]) -> int:
    if _is_goalkeeper(player):
        return 0
    if _is_attacking_player(player):
        return 1
    return 2


def _is_goalkeeper(player: dict[str, Any]) -> bool:
    raw = _normalise_position_tokens(
        player.get("primary_position"),
        player.get("raw_position"),
    )
    return any(token in GOALKEEPER_POSITION_TOKENS for token in raw)


def _is_attacking_player(player: dict[str, Any]) -> bool:
    raw = _normalise_position_tokens(
        player.get("primary_position"),
        player.get("raw_position"),
    )
    return any(token in ATTACKING_POSITION_TOKENS for token in raw)


def _normalise_position_tokens(*values: Any) -> set[str]:
    tokens: set[str] = set()

    for value in values:
        if not value:
            continue

        cleaned = str(value).replace("/", " ").replace("-", " ").replace(",", " ")
        for token in cleaned.split():
            upper = token.strip().upper()
            if upper:
                tokens.add(upper)

        full = str(value).strip().upper()
        if full:
            tokens.add(full)

    return tokens


def _resolve_attacker_reason_label(player: dict[str, Any]) -> str:
    if _is_attacking_player(player):
        return "Lead attacker"
    return "Selected player"


def _resolve_goalkeeper_reason_label(player: dict[str, Any]) -> str:
    if _is_goalkeeper(player):
        return "Starting goalkeeper"
    return "Selected player"

def _shape_spotlight_player(
    team_id: int,
    team_name: str,
    player: dict[str, Any],
    reason_label: str,
    minutes_played: int | None = None,
) -> dict[str, Any]:
    return {
        "team_id": team_id,
        "team_name": team_name or "",
        "player": {
            "id": player.get("id"),
            "name": player.get("player_name") or "",
            "short_name": _build_player_short_name(player),
            "position": player.get("primary_position") or player.get("raw_position") or "",
            "shirt_number": player.get("squad_number"),
            "photo_url": None,
        },
        "minutes_played": minutes_played,
        "reason_label": reason_label,
    }

def _shape_league_snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "position": row.get("position"),
        "team": _shape_overview_team_reference(row.get("team", {})),
        "played": row.get("played"),
        "won": row.get("won"),
        "drawn": row.get("drawn"),
        "lost": row.get("lost"),
        "goals_for": row.get("goals_for"),
        "goals_against": row.get("goals_against"),
        "goal_difference": row.get("goal_difference"),
        "points": row.get("points"),
        "form_label": row.get("form_label") or row.get("form") or None,
    }

def _shape_first_vs_last_table_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "position": row.get("position"),
        "team": _shape_overview_team_reference(row.get("team", {})),
        "played": row.get("played"),
        "won": row.get("won"),
        "drawn": row.get("drawn"),
        "lost": row.get("lost"),
        "goals_for": row.get("goals_for"),
        "goals_against": row.get("goals_against"),
        "goal_difference": row.get("goal_difference"),
        "points": row.get("points"),
        "form_label": row.get("form_label") or row.get("form") or None,
    }

def _shape_match_preview_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "utc_date": item.get("kickoff_at"),
        "status": item.get("status") or None,
        "home_team": _shape_overview_team_reference(item.get("home_team", {})),
        "away_team": _shape_overview_team_reference(item.get("away_team", {})),
        "home_score": item.get("home_score"),
        "away_score": item.get("away_score"),
        "score_line": _build_score_line(item),
        "venue_label": _build_venue_label(item) or None,
    }

def _build_score_line(item: dict[str, Any]) -> str | None:
    home_score = item.get("home_score")
    away_score = item.get("away_score")

    if home_score is None or away_score is None:
        return None

    return f"{home_score}-{away_score}"


def _build_venue_label(item: dict[str, Any]) -> str:
    home_name = _safe_nested_str(item, "home_team", "name")
    away_name = _safe_nested_str(item, "away_team", "name")
    return f"{home_name} vs {away_name}".strip()


def _shape_scorer_player_reference(item: dict[str, Any]) -> dict[str, Any]:
    canonical_player = item.get("canonical_player") or {}
    canonical_display_name = canonical_player.get("display_name") or ""
    player_name = item.get("player_name") or canonical_display_name

    return {
        "id": canonical_player.get("id"),
        "name": player_name or "",
        "short_name": _build_scorer_short_name(item, canonical_player),
        "photo_url": None,
        "position": "",
    }


def _build_top_scorer_identity_key(
    item: dict[str, Any],
    team_ref: dict[str, Any],
) -> str:
    canonical_player = item.get("canonical_player") or {}
    canonical_player_id = canonical_player.get("id")
    if canonical_player_id:
        return f"canonical:{canonical_player_id}"

    external_player_id = str(item.get("external_player_id") or "").strip()
    if external_player_id:
        return f"external:{external_player_id}"

    name_key = _normalise_person_name(str(item.get("player_name") or ""))
    team_key = _normalise_person_name(str(team_ref.get("name") or ""))

    if name_key:
        return f"name_team:{name_key}:{team_key}"

    return f"fallback:{name_key}:{team_key}:{item.get('rank') or 9999}"


def _build_top_scorer_loose_identity_key(
    item: dict[str, Any],
    player_ref: dict[str, Any],
    team_ref: dict[str, Any],
    competition_ref: dict[str, Any],
) -> str:
    display_name = (
        str(player_ref.get("name") or "").strip()
        or str(item.get("player_name") or "").strip()
    )
    name_tokens = _normalise_person_name(display_name).split()
    if not name_tokens:
        return ""

    surname = name_tokens[-1]
    initial = name_tokens[0][:1]
    competition_key = str(competition_ref.get("id") or "")
    team_key = str(team_ref.get("id") or "") or _normalise_person_name(str(team_ref.get("name") or ""))

    if not competition_key or not team_key or not surname:
        return ""

    return f"loose:{competition_key}:{team_key}:{initial}:{surname}"


def _build_top_scorer_coarse_identity_key(
    item: dict[str, Any],
    player_ref: dict[str, Any],
    competition_ref: dict[str, Any],
) -> str:
    display_name = (
        str(player_ref.get("name") or "").strip()
        or str(item.get("player_name") or "").strip()
    )
    name_tokens = _normalise_person_name(display_name).split()
    if not name_tokens:
        return ""

    surname = name_tokens[-1]
    initial = name_tokens[0][:1]
    competition_key = str(competition_ref.get("id") or "")

    if not competition_key or not surname:
        return ""

    return f"coarse:{competition_key}:{initial}:{surname}"


def _is_better_scorer_candidate(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    candidate_score = (
        -(candidate.get("sort_goals") or 0),
        candidate.get("sort_penalties") if candidate.get("sort_penalties") is not None else 9999,
        candidate.get("sort_rank") or 9999,
        candidate.get("sort_name") or "",
    )
    current_score = (
        -(current.get("sort_goals") or 0),
        current.get("sort_penalties") if current.get("sort_penalties") is not None else 9999,
        current.get("sort_rank") or 9999,
        current.get("sort_name") or "",
    )
    return candidate_score < current_score


def _build_top_scorer_summary(item: dict[str, Any]) -> str:
    goals = item.get("goals") or 0
    penalties = item.get("penalties")
    played_matches = item.get("played_matches")
    team_name = _safe_nested_str(item, "team", "name")

    summary_bits = []
    if team_name:
        summary_bits.append(f"{goals} league goals for {team_name}")
    else:
        summary_bits.append(f"{goals} league goals")

    if penalties is not None:
        summary_bits.append(f"{penalties} from the spot")

    if played_matches:
        goals_per_game = goals / played_matches if played_matches else 0
        summary_bits.append(f"{goals_per_game:.2f} goals per game")

    return ", ".join(summary_bits)


def _build_scorer_short_name(
    item: dict[str, Any],
    canonical_player: dict[str, Any],
) -> str:
    display_name = canonical_player.get("display_name") or item.get("player_name") or ""
    first_name = canonical_player.get("first_name") or ""
    last_name = canonical_player.get("last_name") or ""

    if first_name and last_name:
        return f"{first_name[:1]}. {last_name}".strip()

    return display_name


def _build_player_short_name(player: dict[str, Any]) -> str:
    first_name = player.get("first_name") or ""
    last_name = player.get("last_name") or ""
    player_name = player.get("player_name") or ""

    if first_name and last_name:
        return f"{first_name[:1]}. {last_name}".strip()

    if last_name:
        return last_name

    return player_name


def _stringify_player_id(item: dict[str, Any]) -> str:
    canonical_player = item.get("canonical_player") or {}
    player_id = canonical_player.get("id")
    if player_id is not None:
        return str(player_id)

    external_player_id = item.get("external_player_id")
    if external_player_id:
        return str(external_player_id)

    fallback_name = item.get("player_name") or ""
    return fallback_name


def _build_cta(label: str, path: str, query: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": label,
        "path": path,
        "query": query,
    }


def _safe_nested_str(item: dict[str, Any], outer_key: str, inner_key: str) -> str:
    nested = item.get(outer_key) or {}
    value = nested.get(inner_key)
    if value is None:
        return ""
    return str(value)


def _safe_nested_int(item: dict[str, Any], outer_key: str, inner_key: str) -> int | None:
    nested = item.get(outer_key) or {}
    value = nested.get(inner_key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalise_person_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def _form_points(form_label: str) -> int:
    total = 0
    for char in (form_label or "").upper():
        if char == "W":
            total += 3
        elif char == "D":
            total += 1
    return total


def _shape_overview_competition_reference(competition: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": competition.get("id") or 0,
        "code": competition.get("code") or None,
        "name": competition.get("name") or "Live Football",
        "country": competition.get("country") or competition.get("area_name") or None,
        "emblem_url": competition.get("emblem_url") or None,
    }


def _shape_overview_team_reference(team: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": team.get("id"),
        "name": team.get("name") or "Unknown club",
        "short_name": team.get("short_name") or team.get("tla") or None,
        "crest_url": team.get("crest_url") or team.get("emblem_url") or None,
    }


def _resolve_directory_entry_by_name(player_name: str) -> PlayerDirectoryEntry | None:
    cleaned_name = (player_name or "").strip()
    if not cleaned_name:
        return None

    queryset = PlayerDirectoryEntry.objects.select_related(
        "canonical_player",
        "team",
        "team__competition",
    ).filter(is_active=True)

    exact_match = queryset.filter(player_name__iexact=cleaned_name).order_by(
        "-last_synced_at",
        "id",
    ).first()
    if exact_match:
        return exact_match

    name_parts = cleaned_name.split()
    if len(name_parts) >= 2:
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:])
        split_match = queryset.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
        ).order_by(
            "-last_synced_at",
            "id",
        ).first()
        if split_match:
            return split_match

    if name_parts:
        surname_match = queryset.filter(last_name__iexact=name_parts[-1]).order_by(
            "-last_synced_at",
            "id",
        ).first()
        if surname_match:
            return surname_match

    return None


def _shape_overview_player_reference_from_directory(
    directory_entry: PlayerDirectoryEntry | None,
    fallback_name: str,
) -> dict[str, Any]:
    if directory_entry:
        return {
            "id": directory_entry.canonical_player_id,
            "name": directory_entry.player_name or fallback_name or "Unknown player",
            "short_name": _build_player_short_name(
                {
                    "first_name": directory_entry.first_name,
                    "last_name": directory_entry.last_name,
                    "player_name": directory_entry.player_name,
                }
            ),
            "position": directory_entry.primary_position or directory_entry.raw_position or None,
            "shirt_number": directory_entry.squad_number,
            "photo_url": None,
        }

    return {
        "id": None,
        "name": fallback_name or "Unknown player",
        "short_name": fallback_name or "Unknown player",
        "position": None,
        "shirt_number": None,
        "photo_url": None,
    }


def _shape_overview_team_reference_from_directory(
    directory_entry: PlayerDirectoryEntry | None,
) -> dict[str, Any]:
    if directory_entry and directory_entry.team:
        return {
            "id": directory_entry.team_id,
            "name": directory_entry.team.name or "Unknown club",
            "short_name": directory_entry.team.short_name or directory_entry.team.tla or None,
            "crest_url": directory_entry.team.emblem_url or None,
        }

    return {
        "id": None,
        "name": "Unknown club",
        "short_name": None,
        "crest_url": None,
    }


def _shape_overview_competition_reference_from_directory(
    directory_entry: PlayerDirectoryEntry | None,
) -> dict[str, Any]:
    competition = directory_entry.team.competition if directory_entry and directory_entry.team else None

    if competition:
        return {
            "id": competition.id,
            "code": competition.code or None,
            "name": competition.name or "Live Football",
            "country": competition.area_name or None,
            "emblem_url": competition.emblem_url or None,
        }

    return {
        "id": 0,
        "code": None,
        "name": "Live Football",
        "country": None,
        "emblem_url": None,
    }


def _build_hat_trick_summary(date_value: str, match_label: str, result: str) -> str:
    if date_value and match_label and result:
        return f"{date_value}: {match_label} finished {result}."
    if date_value and match_label:
        return f"{date_value}: {match_label}."
    if match_label and result:
        return f"{match_label} finished {result}."
    if match_label:
        return match_label
    if date_value:
        return f"Hat-trick recorded on {date_value}."
    return "Recent tracked hat-trick."


def _build_striker_lull_summary(
    last_scored: str,
    match_label: str,
    no_goal_matches: int | None,
    result: str,
) -> str:
    streak_label = (
        f"No goals in the last {no_goal_matches} matches"
        if no_goal_matches is not None
        else "No recent goals"
    )

    if last_scored and match_label and result:
        return f"{streak_label}. Last scored on {last_scored} in {match_label} ({result})."
    if last_scored and match_label:
        return f"{streak_label}. Last scored on {last_scored} in {match_label}."
    if last_scored:
        return f"{streak_label}. Last goal came on {last_scored}."
    return f"{streak_label}."


def _format_goals_per_game_metric(
    native_goals_per_game: Any,
    scorer_name: str,
    directory_entry: PlayerDirectoryEntry | None,
) -> str:
    if native_goals_per_game is not None:
        try:
            return f"{float(native_goals_per_game):.2f}"
        except (TypeError, ValueError):
            pass

    lookup_name = (directory_entry.player_name if directory_entry else scorer_name) or ""
    if not lookup_name:
        return ""

    scorer = (
        CompetitionTopScorer.objects
        .filter(player_name__iexact=lookup_name)
        .order_by("-synced_at", "-goals", "id")
        .first()
    )
    if not scorer:
        return ""

    played_matches = (scorer.metadata or {}).get("played_matches") or 0
    if played_matches <= 0:
        return ""

    return f"{(scorer.goals / played_matches):.2f}"


def _build_player_trend_query(
    trend: str,
    player_ref: dict[str, Any],
) -> dict[str, Any]:
    query: dict[str, Any] = {"trend": trend}

    player_id = player_ref.get("id")
    if player_id is not None:
        query["playerId"] = player_id
    else:
        query["playerName"] = player_ref.get("name") or ""

    return query