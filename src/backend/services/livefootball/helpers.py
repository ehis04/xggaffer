"""
Helper functions for the livefootball service layer.

Small formatting and lookup tasks handled
Model data converted into the standard dictionary structure used by the API.
"""

from django.db.models import Q
from django.utils import timezone

from common.utils import iso_or_none


# ---------------------------------------------------------------------------
# Fixture status groupings
# ---------------------------------------------------------------------------

# Indicates a match has been played and has a definitive result
FINISHED_STATUSES = {"FINISHED", "AWARDED", "AFTER_EXTRA_TIME", "PENALTY_SHOOTOUT"}

# Indicate a match hasn't yet been played or is in progress
UPCOMING_STATUSES = {"SCHEDULED", "TIMED", "POSTPONED", "SUSPENDED", "IN_PLAY", "PAUSED"}


# ---------------------------------------------------------------------------
# Season label resolution
# ---------------------------------------------------------------------------

# Normalise the requested season label and return an empty string if none was provided
def resolve_requested_season_label(requested_season_label, competition):
    if requested_season_label is None:
        return ""

    cleaned = str(requested_season_label).strip()
    return cleaned

# Work out which season label to use for fixtures based on fixture data, the request, or the competition default
def resolve_fixtures_season_label(fixtures, requested_season_label, competition):
    if fixtures:
        return fixtures[0].season_label or requested_season_label or competition.current_season_label or ""
    return requested_season_label or competition.current_season_label or ""

# Get the most recent table snapshot from the queryset
def resolve_table_snapshot(queryset):
    return queryset.order_by("-season_label", "-matchday", "-synced_at", "-id").first()

# ---------------------------------------------------------------------------
# Fixture splitting
# ---------------------------------------------------------------------------

# Split fixtures into previous and upcoming matches using status and kickoff time
def split_previous_next_fixtures(
    queryset,
    previous_limit=5,
    next_limit=5,
    now=None,
):
    now = now or timezone.now()

    previous_items = list(
        queryset.filter(
            Q(status__in=FINISHED_STATUSES) | Q(kickoff_at__lt=now)
        )
        .order_by("-kickoff_at", "-id")[: int(previous_limit)]
    )

    next_items = list(
        queryset.filter(
            Q(status__in=UPCOMING_STATUSES) | Q(kickoff_at__gte=now) | Q(kickoff_at__isnull=True)
        )
        .exclude(status__in=FINISHED_STATUSES)
        .order_by("kickoff_at", "id")[: int(next_limit)]
    )

    return previous_items, next_items

# ---------------------------------------------------------------------------
# Shape functions — competition and team
# ---------------------------------------------------------------------------

# Convert a competition record into the standard dictionary format used by the API
def shape_competition_item(item):
    return {
        "id": item.id,
        "provider": item.provider,
        "external_id": item.external_id or "",
        "code": item.code or "",
        "name": item.name or "",
        "area_name": item.area_name or "",
        "emblem_url": item.emblem_url or "",
        "current_season_label": item.current_season_label or "",
        "current_season_start_date": iso_or_none(item.current_season_start_date),
        "current_season_end_date": iso_or_none(item.current_season_end_date),
        "current_matchday": item.current_matchday,
        "last_synced_at": iso_or_none(item.last_synced_at),
    }

# Convert a team lookup record into the standard dictionary format used by the API
def shape_team_lookup_item(item):
    return {
        "id": item.id,
        "competition_id": item.competition_id,
        "provider": item.provider,
        "external_id": item.external_id or "",
        "season_label": item.season_label or "",
        "name": item.name or "",
        "short_name": item.short_name or "",
        "tla": item.tla or "",
        "area_name": item.area_name or "",
        "emblem_url": item.emblem_url or "",
        "venue": item.venue or "",
        "website": item.website or "",
        "founded_year": item.founded_year,
        "last_synced_at": iso_or_none(item.last_synced_at),
    }

# Build a team reference dictionary, or return a fallback version if no team is linked
def shape_team_reference(item, external_id="", fallback_name=""):
    if item:
        return {
            "id": item.id,
            "external_id": item.external_id or "",
            "name": item.name or "",
            "short_name": item.short_name or "",
            "tla": item.tla or "",
            "emblem_url": item.emblem_url or "",
        }

    return {
        "id": None,
        "external_id": external_id or "",
        "name": fallback_name or "",
        "short_name": "",
        "tla": "",
        "emblem_url": "",
    }

# Build a player reference dictionary, or return an empty fallback if no player is linked
def shape_canonical_player_reference(item):
    if not item:
        return {
            "id": None,
            "display_name": "",
            "first_name": "",
            "last_name": "",
        }

    return {
        "id": item.id,
        "display_name": getattr(item, "display_name", "") or "",
        "first_name": getattr(item, "first_name", "") or "",
        "last_name": getattr(item, "last_name", "") or "",
    }


# ---------------------------------------------------------------------------
# Shape functions — table and fixtures
# ---------------------------------------------------------------------------

# Convert a league table row into the standard dictionary format used by the API
def shape_table_row(item):
    return {
        "position": item.position,
        "team": shape_team_reference(
            item.team,
            external_id=item.external_team_id or "",
            fallback_name=item.team_name or "",
        ),
        "played": item.played,
        "won": item.won,
        "drawn": item.drawn,
        "lost": item.lost,
        "goals_for": item.goals_for,
        "goals_against": item.goals_against,
        "goal_difference": item.goal_difference,
        "points": item.points,
        "form": item.form or "",
    }

# Convert a fixture into the standard dictionary format used by the API
def shape_fixture(item):
    return {
        "id": item.id,
        "external_match_id": item.external_match_id or "",
        "season_label": item.season_label or "",
        "status": item.status or "",
        "kickoff_at": iso_or_none(item.kickoff_at),
        "matchday": item.matchday,
        "home_team": shape_team_reference(
            item.home_team,
            external_id=item.home_external_team_id or "",
            fallback_name=item.home_team_name or "",
        ),
        "away_team": shape_team_reference(
            item.away_team,
            external_id=item.away_external_team_id or "",
            fallback_name=item.away_team_name or "",
        ),
        "home_score": item.home_score,
        "away_score": item.away_score,
    }


# ---------------------------------------------------------------------------
# Shape functions — scorers and players
# ---------------------------------------------------------------------------

# Convert a top scorer record into the standard dictionary format used by the API
def shape_scorer(item):
    played_matches = (item.metadata or {}).get("played_matches")

    return {
        "rank": item.rank,
        "external_player_id": item.external_player_id or "",
        "player_name": item.player_name or "",
        "goals": item.goals,
        "penalties": item.penalties,
        "played_matches": played_matches,
        "team": shape_team_reference(
            item.team,
            external_id=item.external_team_id or "",
            fallback_name=item.team_name or "",
        ),
        "canonical_player": shape_canonical_player_reference(item.canonical_player),
    }

# Convert a player lookup record into the standard dictionary format used by the API, including team details
def shape_player_lookup_item(item):
    team = item.team

    return {
        "id": item.id,
        "provider": item.provider,
        "external_player_id": item.external_player_id or "",
        "player_name": item.player_name or "",
        "first_name": item.first_name or "",
        "last_name": item.last_name or "",
        "date_of_birth": iso_or_none(item.date_of_birth),
        "nationality": item.nationality or "",
        "primary_position": item.primary_position or "",
        "raw_position": item.raw_position or "",
        "squad_number": item.squad_number,
        "is_active": item.is_active,
        "team": shape_team_lookup_item(team) if team else {
            "id": None,
            "competition_id": None,
            "provider": "",
            "external_id": "",
            "season_label": "",
            "name": "",
            "short_name": "",
            "tla": "",
            "area_name": "",
            "emblem_url": "",
            "venue": "",
            "website": "",
            "founded_year": None,
            "last_synced_at": None,
        },
        "canonical_player": shape_canonical_player_reference(item.canonical_player),
    }
