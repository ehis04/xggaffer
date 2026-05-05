from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.users.permissions import IsReferee
from .serializers import SubmitScenarioSerializer, SubmitDrillSerializer

from apps.referee.progressTracking.services import submit_scenario, submit_drill

# Submits and marks a user's answer for a scenario course item
class SubmitScenarioView(APIView):
    permission_classes = [IsAuthenticated, IsReferee]

    def post(self, request):
        serializer = SubmitScenarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        progress = submit_scenario(
            user_profile=request.user.profile,
            item_id=d['item_id'],
            selected_id=d['selected_id'],
        )

        return Response({
            'correct':   progress.scenario_correct,
            'completed': progress.completed,
        })

# Submits and marks a user's answers for a drill course item
class SubmitDrillView(APIView):
    permission_classes = [IsAuthenticated, IsReferee]

    def post(self, request):
        serializer = SubmitDrillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        progress = submit_drill(
            user_profile=request.user.profile,
            item_id=d['item_id'],
            answers=d['answers'],
        )

        return Response({'completed': progress.completed})