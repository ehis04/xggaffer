from django.db.models import Q

from apps.livefootball.models import (
    Competition,
    CompetitionFixture,
    CompetitionTableSnapshot,
    CompetitionTopScorer,
    PlayerDirectoryEntry,
    TeamDirectoryEntry,
)
from .helpers import (
    iso_or_none,
    resolve_fixtures_season_label,
    resolve_requested_season_label,
    resolve_table_snapshot,
    shape_competition_item,
    shape_fixture,
    shape_player_lookup_item,
    shape_scorer,
    shape_table_row,
    shape_team_lookup_item,
    split_previous_next_fixtures,
)

def list_competitions(provider=None):
    queryset = Competition.objects.all().order_by("name", "id")

    if provider:
        queryset = queryset.filter(provider=provider)

    return [shape_competition_item(item) for item in queryset]


def get_competition_table(competition_id, season_label=None, snapshot_label=None):
    competition = _get_competition(competition_id)

    queryset = CompetitionTableSnapshot.objects.filter(
        competition=competition,
    ).prefetch_related("rows", "rows__team")

    resolved_season_label = resolve_requested_season_label(season_label, competition)
    if resolved_season_label:
        queryset = queryset.filter(season_label=resolved_season_label)

    if snapshot_label:
        queryset = queryset.filter(snapshot_label=snapshot_label)

    snapshot = resolve_table_snapshot(queryset)

    if not snapshot:
        return {
            "competition": shape_competition_item(competition),
            "season_label": resolved_season_label,
            "snapshot_label": snapshot_label or "latest",
            "matchday": None,
            "fetched_at": None,
            "synced_at": None,
            "rows": [],
        }

    rows = snapshot.rows.select_related("team").order_by("position", "id")

    return {
        "competition": shape_competition_item(competition),
        "season_label": snapshot.season_label or "",
        "snapshot_label": snapshot.snapshot_label or "",
        "matchday": snapshot.matchday,
        "fetched_at": iso_or_none(snapshot.fetched_at),
        "synced_at": iso_or_none(snapshot.synced_at),
        "rows": [shape_table_row(item) for item in rows],
    }


def get_competition_fixtures(
    competition_id,
    season_label=None,
    status=None,
    matchday=None,
    limit=None,
):
    competition = _get_competition(competition_id)

    queryset = _competition_fixtures_queryset(
        competition=competition,
        season_label=season_label,
        status=status,
        matchday=matchday,
    )

    if limit:
        queryset = queryset[: int(limit)]

    fixtures = list(queryset)

    return {
        "competition": shape_competition_item(competition),
        "season_label": resolve_fixtures_season_label(fixtures, season_label, competition),
        "count": len(fixtures),
        "items": [shape_fixture(item) for item in fixtures],
    }


def get_competition_previous_next_fixtures(
    competition_id,
    season_label=None,
    previous_limit=5,
    next_limit=5,
):
    competition = _get_competition(competition_id)

    base_queryset = _competition_fixtures_queryset(
        competition=competition,
        season_label=season_label,
    )

    previous_items, next_items = split_previous_next_fixtures(
        base_queryset,
        previous_limit=previous_limit,
        next_limit=next_limit,
    )

    return {
        "competition": shape_competition_item(competition),
        "season_label": (
            resolve_fixtures_season_label(previous_items, season_label, competition)
            or resolve_fixtures_season_label(next_items, season_label, competition)
        ),
        "previous": [shape_fixture(item) for item in previous_items],
        "next": [shape_fixture(item) for item in next_items],
    }


def get_competition_scorers(competition_id, season_label=None, limit=None):
    competition = _get_competition(competition_id)

    queryset = CompetitionTopScorer.objects.select_related(
        "canonical_player",
        "team",
        "competition",
    ).filter(
        competition=competition,
    )

    resolved_season_label = resolve_requested_season_label(season_label, competition)
    if resolved_season_label:
        queryset = queryset.filter(season_label=resolved_season_label)

    queryset = queryset.order_by("rank", "id")

    if limit:
        queryset = queryset[: int(limit)]

    scorers = list(queryset)

    if scorers and not season_label:
        resolved_season_label = scorers[0].season_label or resolved_season_label

    return {
        "competition": shape_competition_item(competition),
        "season_label": resolved_season_label,
        "count": len(scorers),
        "items": [shape_scorer(item) for item in scorers],
    }


def list_competition_teams(competition_id, season_label=None):
    competition = _get_competition(competition_id)

    queryset = TeamDirectoryEntry.objects.filter(
        competition=competition,
    ).order_by("name", "id")

    resolved_season_label = resolve_requested_season_label(season_label, competition)
    if resolved_season_label:
        queryset = queryset.filter(season_label=resolved_season_label)

    teams = list(queryset)

    if teams and not season_label:
        resolved_season_label = teams[0].season_label or resolved_season_label

    return {
        "competition": shape_competition_item(competition),
        "season_label": resolved_season_label,
        "count": len(teams),
        "items": [shape_team_lookup_item(item) for item in teams],
    }


def list_team_players(team_id, active_only=True):
    team = _get_team(team_id)

    queryset = PlayerDirectoryEntry.objects.select_related(
        "canonical_player",
        "team",
        "team__competition",
    ).filter(
        team=team,
    ).order_by("player_name", "id")

    if active_only:
        queryset = queryset.filter(is_active=True)

    players = list(queryset)

    return {
        "team": shape_team_lookup_item(team),
        "competition": shape_competition_item(team.competition),
        "season_label": team.season_label or "",
        "count": len(players),
        "items": [shape_player_lookup_item(item) for item in players],
    }


def list_competition_players(competition_id, season_label=None, active_only=True):
    competition = _get_competition(competition_id)

    queryset = PlayerDirectoryEntry.objects.select_related(
        "canonical_player",
        "team",
        "team__competition",
    ).filter(
        team__competition=competition,
    ).order_by("player_name", "id")

    resolved_season_label = resolve_requested_season_label(season_label, competition)
    if resolved_season_label:
        queryset = queryset.filter(team__season_label=resolved_season_label)

    if active_only:
        queryset = queryset.filter(is_active=True)

    players = list(queryset)

    return {
        "competition": shape_competition_item(competition),
        "season_label": resolved_season_label,
        "count": len(players),
        "items": [shape_player_lookup_item(item) for item in players],
    }


def search_players(
    query,
    competition_id=None,
    team_id=None,
    season_label=None,
    active_only=True,
    limit=20,
):
    cleaned_query = (query or "").strip()

    queryset = PlayerDirectoryEntry.objects.select_related(
        "canonical_player",
        "team",
        "team__competition",
    ).all()

    if active_only:
        queryset = queryset.filter(is_active=True)

    if competition_id:
        queryset = queryset.filter(team__competition_id=competition_id)

    if team_id:
        queryset = queryset.filter(team_id=team_id)

    if season_label:
        queryset = queryset.filter(team__season_label=season_label)

    if cleaned_query:
        queryset = queryset.filter(
            Q(player_name__icontains=cleaned_query)
            | Q(first_name__icontains=cleaned_query)
            | Q(last_name__icontains=cleaned_query)
            | Q(team__name__icontains=cleaned_query)
            | Q(team__short_name__icontains=cleaned_query)
        )

    queryset = queryset.order_by("player_name", "id").distinct()[: int(limit)]

    items = [shape_player_lookup_item(item) for item in queryset]

    return {
        "query": cleaned_query,
        "count": len(items),
        "items": items,
    }


def _get_competition(competition_id):
    return Competition.objects.get(pk=competition_id)


def _get_team(team_id):
    return TeamDirectoryEntry.objects.select_related("competition").get(pk=team_id)


def _competition_fixtures_queryset(
    competition,
    season_label=None,
    status=None,
    matchday=None,
):
    queryset = CompetitionFixture.objects.select_related(
        "competition",
        "home_team",
        "away_team",
    ).filter(
        competition=competition,
    )

    resolved_season_label = resolve_requested_season_label(season_label, competition)
    if resolved_season_label:
        queryset = queryset.filter(season_label=resolved_season_label)

    if status:
        queryset = queryset.filter(status=status)

    if matchday is not None and matchday != "":
        queryset = queryset.filter(matchday=matchday)

    return queryset.order_by("kickoff_at", "id")