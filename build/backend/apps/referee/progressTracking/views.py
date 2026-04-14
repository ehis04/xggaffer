from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers as drf_serializers

from .serializers import (
    ActiveCourseSerializer,
    LawCourseSerializer,
    StreakSerializer,
    PerformanceSerializer,
    MarkItemCompleteSerializer,
)
from . import services


class RefereeDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        up            = request.user.profile
        active_course = services.get_active_course(up)

        return Response({
            'active_course': ActiveCourseSerializer(active_course).data
                             if active_course else None,
            'courses':       LawCourseSerializer(
                                 services.get_all_courses(up), many=True).data,
            'streak':        StreakSerializer(services.get_streak(up)).data,
            'performance':   PerformanceSerializer(services.get_performance(up)).data,
        })


class MarkItemCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MarkItemCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        progress = services.mark_item_complete(
            user_profile=request.user.profile,
            item_id=serializer.validated_data['item_id'],
        )

        return Response({'completed': progress.completed})


class SubmitScenarioView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        item_id     = request.data.get('item_id')
        selected_id = request.data.get('selected_id')

        if not item_id or not selected_id:
            raise drf_serializers.ValidationError(
                "Both item_id and selected_id are required."
            )

        progress = services.submit_scenario(
            user_profile=request.user.profile,
            item_id=int(item_id),
            selected_id=str(selected_id),
        )

        return Response({
            'correct':   progress.scenario_correct,
            'completed': progress.completed,
        })


class SubmitDrillView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        item_id = request.data.get('item_id')
        answers = request.data.get('answers')

        if not item_id or answers is None:
            raise drf_serializers.ValidationError(
                "Both item_id and answers are required."
            )

        for key, val in answers.items():
            if val not in ('true', 'false'):
                raise drf_serializers.ValidationError(
                    f"Answer values must be 'true' or 'false', got '{val}'."
                )

        progress = services.submit_drill(
            user_profile=request.user.profile,
            item_id=int(item_id),
            answers=answers,
        )

        return Response({'completed': progress.completed})