from rest_framework import serializers
from .models import Teamsheet, TeamsheetPlayer


class TeamsheetPlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamsheetPlayer
        fields = '__all__'


class TeamsheetSerializer(serializers.ModelSerializer):
    players = TeamsheetPlayerSerializer(many=True, read_only=True)

    class Meta:
        model = Teamsheet
        fields = '__all__'
