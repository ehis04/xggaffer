from rest_framework import serializers
from .models import FitbitToken, DailyActivitySummary

class DailyActivitySerializer(serializers.Serializer):
    class Meta:
        model = DailyActivitySummary
        fields = [
            "id",
            "date",
            "steps",
            "calories_burned",
            "active_minutes",
            "distance_km",
            "resting_heart_rate",
            "heart_rate_zones",
            "synced_at",
        ]
        read_only_fields = fields
        
class FitbitTokenSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)
    is_connected = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = FitbitToken
        fields = [
            "fitbit_user_id",
            "connected_at",
            "last_synced_at",
            "is_expired",
            "is_connected",
        ]
        read_only_fields = fields