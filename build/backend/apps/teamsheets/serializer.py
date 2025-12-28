from .models import *
from rest_framework import serializers

class TeamsheeetSerializer(serializers.ModelSerializer):
    players = TeamsheetPlayerSerializer(many=True, read_only=True)
    
    class Meta:
        model = Teamsheet
        fields = __all__

class TeamsheetPlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = __all__ 

