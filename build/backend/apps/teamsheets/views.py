from django.shortcuts import render
from rest_framework import viewsets
from .models import Teamsheet, TeamsheetPlayer
from .serializers import TeamsheetSerializer, TeamsheetPlayerSerializer


class TeamsheetViewSet(viewsets.ModelViewSet):
    queryset = Teamsheet.objects.all()
    serializer_class = TeamsheetSerializer


class TeamsheetPlayerViewSet(viewsets.ModelViewSet):
    queryset = TeamsheetPlayer.objects.all()
    serializer_class = TeamsheetPlayerSerializer

