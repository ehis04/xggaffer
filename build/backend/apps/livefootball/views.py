from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LiveFootballOverviewSerializer
from .services.overview import get_livefootball_homepage_payload
from .services.exceptions import TeamMappingNotFoundError
from .services.league_data import (
    create_saved_league_scenario,
    delete_saved_league_scenario,
    get_league_compare_payload,
    get_league_expected_table_payload,
    get_league_scenario_payload,
    get_leagues_meta_payload,
    get_saved_league_scenario_detail,
    list_saved_league_scenarios,
)

from .serializers import (
    CompetitionFixturesResponseSerializer,
    CompetitionListItemSerializer,
    CompetitionPlayersResponseSerializer,
    CompetitionPreviousNextFixturesResponseSerializer,
    CompetitionScorersResponseSerializer,
    CompetitionTableResponseSerializer,
    CompetitionTeamsResponseSerializer,
    PlayerSearchResponseSerializer,
    TeamPlayersResponseSerializer,
    LeagueCompareResponseSerializer,
    LeagueExpectedTableResponseSerializer,
    LeaguesMetaResponseSerializer,
    LeagueScenarioRequestSerializer,
    LeagueScenarioResponseSerializer,
    SavedLeagueScenarioCreateSerializer,
    SavedLeagueScenarioDetailSerializer,
    SavedLeagueScenarioListResponseSerializer,
)
from services.livefootball.queries import (
    get_competition_fixtures,
    get_competition_previous_next_fixtures,
    get_competition_scorers,
    get_competition_table,
    list_competition_players,
    list_competition_teams,
    list_competitions,
    list_team_players,
    search_players,
)

from rest_framework.permissions import IsAuthenticated

class LiveFootballProtectedAPIView(APIView):
    permission_classes = [IsAuthenticated]

class CompetitionListView(LiveFootballProtectedAPIView):
    def get(self, request):
        provider = request.query_params.get("provider")
        payload = list_competitions(provider=provider)
        serializer = CompetitionListItemSerializer(payload, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompetitionTableView(LiveFootballProtectedAPIView):
    def get(self, request, competition_id):
        season_label = request.query_params.get("season")
        snapshot_label = request.query_params.get("snapshot")

        try:
            payload = get_competition_table(
                competition_id=competition_id,
                season_label=season_label,
                snapshot_label=snapshot_label,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompetitionTableResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompetitionFixturesView(LiveFootballProtectedAPIView):
    def get(self, request, competition_id):
        season_label = request.query_params.get("season")
        status_filter = request.query_params.get("status")
        matchday = self._parse_optional_int(request.query_params.get("matchday"), "matchday")
        limit = self._parse_optional_int(request.query_params.get("limit"), "limit")

        try:
            payload = get_competition_fixtures(
                competition_id=competition_id,
                season_label=season_label,
                status=status_filter,
                matchday=matchday,
                limit=limit,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompetitionFixturesResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _parse_optional_int(self, value, field_name):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({field_name: "Must be an integer."})


class CompetitionPreviousNextFixturesView(LiveFootballProtectedAPIView):
    def get(self, request, competition_id):
        season_label = request.query_params.get("season")
        previous_limit = self._parse_limit(
            request.query_params.get("previous_limit"),
            default=5,
            field_name="previous_limit",
        )
        next_limit = self._parse_limit(
            request.query_params.get("next_limit"),
            default=5,
            field_name="next_limit",
        )

        try:
            payload = get_competition_previous_next_fixtures(
                competition_id=competition_id,
                season_label=season_label,
                previous_limit=previous_limit,
                next_limit=next_limit,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompetitionPreviousNextFixturesResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _parse_limit(self, value, default, field_name):
        if value in (None, ""):
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise ValidationError({field_name: "Must be an integer."})
        if parsed <= 0:
            raise ValidationError({field_name: "Must be greater than 0."})
        return parsed


class CompetitionScorersView(LiveFootballProtectedAPIView):
    def get(self, request, competition_id):
        season_label = request.query_params.get("season")
        limit = self._parse_optional_int(request.query_params.get("limit"), "limit")

        try:
            payload = get_competition_scorers(
                competition_id=competition_id,
                season_label=season_label,
                limit=limit,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompetitionScorersResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _parse_optional_int(self, value, field_name):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({field_name: "Must be an integer."})


class CompetitionTeamsView(LiveFootballProtectedAPIView):
    def get(self, request, competition_id):
        season_label = request.query_params.get("season")

        try:
            payload = list_competition_teams(
                competition_id=competition_id,
                season_label=season_label,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompetitionTeamsResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TeamPlayersView(LiveFootballProtectedAPIView):
    def get(self, request, team_id):
        active_only = self._parse_bool(
            request.query_params.get("active_only"),
            default=True,
            field_name="active_only",
        )

        try:
            payload = list_team_players(
                team_id=team_id,
                active_only=active_only,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Team not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TeamPlayersResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _parse_bool(self, value, default, field_name):
        if value in (None, ""):
            return default
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
        raise ValidationError({field_name: "Must be a boolean."})


class CompetitionPlayersView(LiveFootballProtectedAPIView):
    def get(self, request, competition_id):
        season_label = request.query_params.get("season")
        active_only = self._parse_bool(
            request.query_params.get("active_only"),
            default=True,
            field_name="active_only",
        )

        try:
            payload = list_competition_players(
                competition_id=competition_id,
                season_label=season_label,
                active_only=active_only,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompetitionPlayersResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _parse_bool(self, value, default, field_name):
        if value in (None, ""):
            return default
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
        raise ValidationError({field_name: "Must be a boolean."})


class PlayerSearchView(LiveFootballProtectedAPIView):
    def get(self, request):
        query = request.query_params.get("q", "")
        competition_id = self._parse_optional_int(
            request.query_params.get("competition_id"),
            "competition_id",
        )
        team_id = self._parse_optional_int(
            request.query_params.get("team_id"),
            "team_id",
        )
        season_label = request.query_params.get("season")
        active_only = self._parse_bool(
            request.query_params.get("active_only"),
            default=True,
            field_name="active_only",
        )
        limit = self._parse_limit(
            request.query_params.get("limit"),
            default=20,
            field_name="limit",
        )

        payload = search_players(
            query=query,
            competition_id=competition_id,
            team_id=team_id,
            season_label=season_label,
            active_only=active_only,
            limit=limit,
        )

        serializer = PlayerSearchResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _parse_optional_int(self, value, field_name):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({field_name: "Must be an integer."})

    def _parse_limit(self, value, default, field_name):
        if value in (None, ""):
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise ValidationError({field_name: "Must be an integer."})
        if parsed <= 0:
            raise ValidationError({field_name: "Must be greater than 0."})
        return parsed

    def _parse_bool(self, value, default, field_name):
        if value in (None, ""):
            return default
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
        raise ValidationError({field_name: "Must be a boolean."})
class LiveFootballOverviewView(LiveFootballProtectedAPIView):
    def get(self, request):
        payload = get_livefootball_homepage_payload()
        serializer = LiveFootballOverviewSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LeaguesMetaView(LiveFootballProtectedAPIView):
    def get(self, request):
        payload = get_leagues_meta_payload()
        serializer = LeaguesMetaResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeagueExpectedTableView(LiveFootballProtectedAPIView):
    def get(self, request, competition_id):
        season_label = request.query_params.get("season")
        mode = request.query_params.get("mode")
        projection_window = request.query_params.get("projection_window")
        matchweek = self._parse_optional_int(
            request.query_params.get("matchweek"),
            "matchweek",
        )

        try:
            payload = get_league_expected_table_payload(
                competition_id=competition_id,
                season_label=season_label,
                mode=mode,
                matchweek=matchweek,
                projection_window=projection_window,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except TeamMappingNotFoundError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LeagueExpectedTableResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _parse_optional_int(self, value, field_name):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({field_name: "Must be an integer."})
        serializer = LeagueExpectedTableResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LeagueCompareView(LiveFootballProtectedAPIView):
    def get(self, request, competition_id):
        season_label = request.query_params.get("season")
        mode = request.query_params.get("mode")
        projection_window = request.query_params.get("projection_window")
        matchweek = self._parse_optional_int(
            request.query_params.get("matchweek"),
            "matchweek",
        )

        try:
            payload = get_league_compare_payload(
                competition_id=competition_id,
                season_label=season_label,
                mode=mode,
                matchweek=matchweek,
                projection_window=projection_window,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except TeamMappingNotFoundError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LeagueCompareResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _parse_optional_int(self, value, field_name):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({field_name: "Must be an integer."})
        serializer = LeagueCompareResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LeagueScenarioView(LiveFootballProtectedAPIView):
    def post(self, request, competition_id):
        season_label = request.query_params.get("season")
        mode = request.query_params.get("mode")
        matchweek = self._parse_optional_int(
            request.query_params.get("matchweek"),
            "matchweek",
        )

        request_serializer = LeagueScenarioRequestSerializer(data=request.data or {})
        request_serializer.is_valid(raise_exception=True)

        try:
            payload = get_league_scenario_payload(
                competition_id=competition_id,
                season_label=season_label,
                mode=mode,
                matchweek=matchweek,
                locked_results=request_serializer.validated_data.get("locked_results", []),
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except TeamMappingNotFoundError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LeagueScenarioResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _parse_optional_int(self, value, field_name):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({field_name: "Must be an integer."})

class LeagueSavedScenarioListCreateView(LiveFootballProtectedAPIView):
    def get(self, request, competition_id):
        season_label = request.query_params.get("season")
        mode = request.query_params.get("mode")
        matchweek = self._parse_optional_int(
            request.query_params.get("matchweek"),
            "matchweek",
        )

        try:
            payload = list_saved_league_scenarios(
                request.user,
                competition_id=competition_id,
                season_label=season_label,
                mode=mode,
                based_on_matchweek=matchweek,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SavedLeagueScenarioListResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, competition_id):
        season_label = request.query_params.get("season")
        mode = request.query_params.get("mode")
        matchweek = self._parse_optional_int(
            request.query_params.get("matchweek"),
            "matchweek",
        )

        request_serializer = SavedLeagueScenarioCreateSerializer(data=request.data or {})
        request_serializer.is_valid(raise_exception=True)

        try:
            payload = create_saved_league_scenario(
                request.user,
                competition_id=competition_id,
                season_label=season_label,
                mode=mode,
                matchweek=matchweek,
                title=request_serializer.validated_data["title"],
                description=request_serializer.validated_data.get("description", ""),
                locked_results=request_serializer.validated_data.get("locked_results", []),
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Competition not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except TeamMappingNotFoundError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SavedLeagueScenarioDetailSerializer(payload)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _parse_optional_int(self, value, field_name):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({field_name: "Must be an integer."})


class LeagueSavedScenarioDetailView(LiveFootballProtectedAPIView):
    def get(self, request, scenario_id):
        try:
            payload = get_saved_league_scenario_detail(
                request.user,
                scenario_id=scenario_id,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Saved scenario not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SavedLeagueScenarioDetailSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, scenario_id):
        try:
            delete_saved_league_scenario(
                request.user,
                scenario_id=scenario_id,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Saved scenario not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
        
    def _parse_optional_int(self, value, field_name):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({field_name: "Must be an integer."})