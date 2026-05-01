from __future__ import annotations

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.predictions.serializers.widget_payload import WidgetPayloadSerializer

SUPPORTED_WIDGET_INTENTS = [
    "match-prediction",
    "scoreline",
    "projected-table",
    "availability",
    "predicted-lineup",
    "tactical-summary",
    "model-trust",
]

PUBLIC_WIDGET_INTENTS = {"match-prediction", "scoreline", "projected-table", "tactical-summary"}


class WidgetBaseView(APIView):
    widget_intent: str = ""

    def get_permissions(self):
        if self.widget_intent in PUBLIC_WIDGET_INTENTS:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_widget_data(self, request: Request) -> dict:
        raise NotImplementedError

    def get(self, request: Request) -> Response:
        if self.widget_intent not in SUPPORTED_WIDGET_INTENTS:
            return Response(
                {"error": f"Unsupported widget intent: {self.widget_intent}"},
                status=400,
            )
        payload = self.get_widget_data(request)
        serializer = WidgetPayloadSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=200)