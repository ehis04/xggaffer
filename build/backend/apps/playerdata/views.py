import inspect

from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .envelope import build_playerdata_envelope
from services.playerdata import comparisons, queries, summaries
from services.playeroverview import queries as overview_queries

from .serializers import (
    ClubSeasonEnrichmentSummarySerializer,
    EnrichedPlayerListItemSerializer,
    PlayerComparisonSerializer,
    PlayerOverviewComparisonSerializer,
    PlayerOverviewSerializer,
    PlayerSeasonEnrichmentSummarySerializer,
)


def _get_query_param(request, key: str) -> str | None:
    value = request.query_params.get(key)
    if value is None:
        return None

    value = str(value).strip()
    return value or None


def _get_int_query_param(request, key: str) -> int | None:
    value = _get_query_param(request, key)
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({key: "Must be an integer."}) from exc


def _get_bool_query_param(request, key: str) -> bool | None:
    value = _get_query_param(request, key)
    if value is None:
        return None

    normalised = value.lower()
    if normalised in {"true", "1", "yes"}:
        return True
    if normalised in {"false", "0", "no"}:
        return False

    raise ValidationError({key: "Must be a boolean."})


def _get_common_filters(request) -> dict:
    return {
        "provider": _get_query_param(request, "provider"),
        "season_label": _get_query_param(request, "season_label"),
        "season": _get_query_param(request, "season"),
        "competition_code": _get_query_param(request, "competition_code"),
        "competition_name": _get_query_param(request, "competition_name"),
    }


def _filter_kwargs_for_callable(func, candidate_kwargs: dict) -> dict:
    signature = inspect.signature(func)
    accepts_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )

    filtered_kwargs = {}
    for key, value in candidate_kwargs.items():
        if value is None:
            continue
        if accepts_kwargs or key in signature.parameters:
            filtered_kwargs[key] = value

    return filtered_kwargs


def _try_call(module, function_names: list[str], **candidate_kwargs):
    last_type_error = None

    for function_name in function_names:
        func = getattr(module, function_name, None)
        if not callable(func):
            continue

        try:
            filtered_kwargs = _filter_kwargs_for_callable(func, candidate_kwargs)
            return func(**filtered_kwargs)
        except TypeError as exc:
            last_type_error = exc
            continue

    if last_type_error is not None:
        raise ImproperlyConfigured(
            f"Matched a service function in {module.__name__}, but the expected "
            f"arguments do not line up with the playerdata view contract. "
            f"Last TypeError: {last_type_error}"
        ) from last_type_error

    return None


def _raise_service_validation_error(exc: Exception) -> None:
    raise ValidationError({"detail": str(exc)}) from exc


class BasePlayerDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    player_summary_function_names = [
        "get_player_season_summary",
        "build_player_season_summary",
        "summarise_player_season",
        "summarize_player_season",
        "build_player_summary_payload",
    ]
    player_query_function_names = [
        "get_player_season_enrichment",
        "get_player_enrichment",
        "get_player_season_record",
        "get_player_season_data",
        "get_player_summary_context",
    ]

    club_summary_function_names = [
        "get_club_season_summary",
        "build_club_season_summary",
        "summarise_club_season",
        "summarize_club_season",
        "build_club_summary_payload",
    ]
    club_query_function_names = [
        "get_club_season_enrichment",
        "get_club_enrichment",
        "get_club_season_record",
        "get_club_season_data",
        "get_club_summary_context",
    ]

    comparison_function_names = [
        "compare_players",
        "get_player_comparison",
        "build_player_comparison",
        "compare_player_seasons",
    ]

    enriched_player_list_function_names = [
        "list_enriched_players",
        "filter_enriched_players",
        "get_enriched_players",
        "list_player_enrichment",
        "list_player_season_enrichment",
    ]

    player_overview_function_names = [
        "get_player_overview",
        "build_player_overview",
    ]

    player_overview_comparison_function_names = [
        "compare_players_overview",
        "get_player_overview_comparison",
        "build_players_overview_comparison",
    ]

    def get_player_summary_payload(self, player_id: int, filters: dict) -> dict:
        try:
            summary_payload = _try_call(
                summaries,
                self.player_summary_function_names,
                player_id=player_id,
                **filters,
            )
            if summary_payload is not None:
                return summary_payload

            enrichment = _try_call(
                queries,
                self.player_query_function_names,
                player_id=player_id,
                **filters,
            )
            if enrichment is None:
                raise NotFound(
                    "No player season summary data was found for the requested filters."
                )

            summary_payload = _try_call(
                summaries,
                self.player_summary_function_names,
                player_id=player_id,
                enrichment=enrichment,
                **filters,
            )
            if summary_payload is not None:
                return summary_payload

            return enrichment
        except ValueError as exc:
            _raise_service_validation_error(exc)

    def get_club_summary_payload(self, club_id: int, filters: dict) -> dict:
        try:
            summary_payload = _try_call(
                summaries,
                self.club_summary_function_names,
                club_id=club_id,
                **filters,
            )
            if summary_payload is not None:
                return summary_payload

            enrichment = _try_call(
                queries,
                self.club_query_function_names,
                club_id=club_id,
                **filters,
            )
            if enrichment is None:
                raise NotFound(
                    "No club season summary data was found for the requested filters."
                )

            summary_payload = _try_call(
                summaries,
                self.club_summary_function_names,
                club_id=club_id,
                enrichment=enrichment,
                **filters,
            )
            if summary_payload is not None:
                return summary_payload

            return enrichment
        except ValueError as exc:
            _raise_service_validation_error(exc)

    def get_comparison_payload(
        self, player_a_id: int, player_b_id: int, filters: dict
    ) -> dict:
        try:
            payload = _try_call(
                comparisons,
                self.comparison_function_names,
                player_a_id=player_a_id,
                player_b_id=player_b_id,
                **filters,
            )
        except ValueError as exc:
            _raise_service_validation_error(exc)

        if payload is None:
            raise NotFound(
                "No comparison data was found for the requested players/filters."
            )

        return payload

    def get_enriched_player_list_payload(self, request, filters: dict):
        list_filters = {
            **filters,
            "club_id": _get_int_query_param(request, "club_id"),
            "position": _get_query_param(request, "position"),
            "search": _get_query_param(request, "search"),
            "ordering": _get_query_param(request, "ordering"),
            "limit": _get_int_query_param(request, "limit"),
            "include_unavailable": _get_bool_query_param(
                request, "include_unavailable"
            ),
        }

        try:
            payload = _try_call(
                queries,
                self.enriched_player_list_function_names,
                **list_filters,
            )
        except ValueError as exc:
            _raise_service_validation_error(exc)

        if payload is None:
            raise NotFound(
                "No enriched player list data was found for the requested filters."
            )

        return payload

    def get_player_overview_payload(self, player_id: int, filters: dict) -> dict:
        try:
            payload = _try_call(
                overview_queries,
                self.player_overview_function_names,
                player_id=player_id,
                **filters,
            )
        except ValueError as exc:
            _raise_service_validation_error(exc)

        if payload is None:
            raise NotFound(
                "No merged player overview data was found for the requested filters."
            )

        return payload

    def get_player_overview_comparison_payload(
        self, player_a_id: int, player_b_id: int, filters: dict
    ) -> dict:
        try:
            payload = _try_call(
                overview_queries,
                self.player_overview_comparison_function_names,
                player_a_id=player_a_id,
                player_b_id=player_b_id,
                **filters,
            )
        except ValueError as exc:
            _raise_service_validation_error(exc)

        if payload is None:
            raise NotFound(
                "No merged player overview comparison data was found for the requested players/filters."
            )

        return payload


class PlayerSeasonSummaryView(BasePlayerDataAPIView):
    def get(self, request, player_id: int):
        filters = _get_common_filters(request)
        try:
            payload = self.get_player_summary_payload(player_id=player_id, filters=filters)
        except NotFound:
            return Response(build_playerdata_envelope(None))
        serializer = PlayerSeasonEnrichmentSummarySerializer(payload)
        return Response(build_playerdata_envelope(serializer.data))


class ClubSeasonSummaryView(BasePlayerDataAPIView):
    def get(self, request, club_id: int):
        filters = _get_common_filters(request)
        payload = self.get_club_summary_payload(club_id=club_id, filters=filters)
        serializer = ClubSeasonEnrichmentSummarySerializer(payload)
        return Response(build_playerdata_envelope(serializer.data))


class PlayerComparisonView(BasePlayerDataAPIView):
    def get(self, request):
        player_a_id = _get_int_query_param(request, "player_a_id")
        player_b_id = _get_int_query_param(request, "player_b_id")

        if player_a_id is None:
            raise ValidationError({"player_a_id": "This query parameter is required."})
        if player_b_id is None:
            raise ValidationError({"player_b_id": "This query parameter is required."})
        if player_a_id == player_b_id:
            raise ValidationError(
                {"player_b_id": "Comparison requires two different players."}
            )

        filters = _get_common_filters(request)
        payload = self.get_comparison_payload(
            player_a_id=player_a_id,
            player_b_id=player_b_id,
            filters=filters,
        )
        serializer = PlayerComparisonSerializer(payload)
        return Response(build_playerdata_envelope(serializer.data))


class EnrichedPlayerListView(BasePlayerDataAPIView):
    def get(self, request):
        filters = _get_common_filters(request)
        payload = self.get_enriched_player_list_payload(request=request, filters=filters)

        if isinstance(payload, dict):
            raw_results = payload.get("results", payload.get("items", []))
            count = payload.get("count", len(raw_results))
        else:
            raw_results = payload
            count = len(raw_results)

        serializer = EnrichedPlayerListItemSerializer(raw_results, many=True)
        return Response(
            build_playerdata_envelope({
                "count": count,
                "results": serializer.data,
            })
        )


class PlayerOverviewView(BasePlayerDataAPIView):
    def get(self, request, player_id: int):
        filters = {
            **_get_common_filters(request),
            "club_id": _get_int_query_param(request, "club_id"),
            "active_only": _get_bool_query_param(request, "active_only"),
        }
        payload = self.get_player_overview_payload(player_id=player_id, filters=filters)
        serializer = PlayerOverviewSerializer(payload)
        return Response(build_playerdata_envelope(serializer.data))


class PlayerOverviewComparisonView(BasePlayerDataAPIView):
    def get(self, request):
        player_a_id = _get_int_query_param(request, "player_a_id")
        player_b_id = _get_int_query_param(request, "player_b_id")

        if player_a_id is None:
            raise ValidationError({"player_a_id": "This query parameter is required."})
        if player_b_id is None:
            raise ValidationError({"player_b_id": "This query parameter is required."})
        if player_a_id == player_b_id:
            raise ValidationError(
                {"player_b_id": "Comparison requires two different players."}
            )

        filters = {
            **_get_common_filters(request),
            "club_a_id": _get_int_query_param(request, "club_a_id"),
            "club_b_id": _get_int_query_param(request, "club_b_id"),
            "active_only": _get_bool_query_param(request, "active_only"),
        }

        payload = self.get_player_overview_comparison_payload(
            player_a_id=player_a_id,
            player_b_id=player_b_id,
            filters=filters,
        )
        serializer = PlayerOverviewComparisonSerializer(payload)
        return Response(build_playerdata_envelope(serializer.data))