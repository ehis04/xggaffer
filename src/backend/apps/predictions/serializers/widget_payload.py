from __future__ import annotations

from rest_framework import serializers


class WidgetFreshnessSerializer(serializers.Serializer):
    snapshot_published_at = serializers.CharField(allow_null=True)
    staleness_status = serializers.CharField(allow_null=True, required=False)
    is_stale = serializers.BooleanField()
    is_degraded = serializers.BooleanField(default=False)
    stale_reason = serializers.CharField(allow_null=True)
    cascade_degraded = serializers.BooleanField()
    cascade_reason = serializers.CharField(allow_null=True)


class WidgetConfidenceSerializer(serializers.Serializer):
    score = serializers.FloatField()
    band = serializers.ChoiceField(choices=["high", "medium", "low"])


class WidgetPayloadSerializer(serializers.Serializer):
    widget_type = serializers.CharField()
    data = serializers.DictField(allow_null=True)
    explanation = serializers.DictField()
    confidence = WidgetConfidenceSerializer()
    freshness = WidgetFreshnessSerializer()
    summary = serializers.DictField()