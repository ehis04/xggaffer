from django.shortcuts import render
from .models import *
from .serializers import *
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action   
from django.shortcuts import get_object_or_404

class LawEditionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LawEdition.objects.all()
    serializer_class = LawEditionSerializer
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        edition = LawEdition.objects.filter(is_current=True).first()
        if not edition:
            return Response({'error': 'No current edition set'}, status=404)
        serializer = self.get_serializer(edition)
        return Response(serializer.data)

class LawViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LawSerializer
    
    def get_queryset(self):
        queryset = Law.objects.select_related('edition').prefetch_related('clauses')
        
        edition_id = self.request.query_params.get('edition')
        if edition_id:
            queryset = queryset.filter(edition_id=edition_id)
        else:
            current_edition = LawEdition.objects.filter(is_current=True).first()
            if current_edition:
                queryset = queryset.filter(edition=current_edition)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = LawListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_number(self, request):
        law_number = request.query_params.get('number')
        if not law_number:
            return Response({'error': 'number parameter required'}, status=400)
        
        edition_id = request.query_params.get('edition')
        if edition_id:
            law = get_object_or_404(Law, number=law_number, edition_id=edition_id)
        else:
            current_edition = LawEdition.objects.filter(is_current=True).first()
            law = get_object_or_404(Law, number=law_number, edition=current_edition)
        
        serializer = LawSerializer(law)
        return Response(serializer.data)

class LawChangeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LawChangeSerializer
    
    def get_queryset(self):
        queryset = LawChange.objects.select_related('edition')
        
        edition_id = self.request.query_params.get('edition')
        if edition_id:
            queryset = queryset.filter(edition_id=edition_id)
        
        law_number = self.request.query_params.get('law_number')
        if law_number:
            queryset = queryset.filter(law_number=law_number)
        
        return queryset

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LawEditionViewSet, LawViewSet, LawChangeViewSet

router = DefaultRouter()
router.register(r'editions', LawEditionViewSet, basename='edition')
router.register(r'laws', LawViewSet, basename='law')
router.register(r'changes', LawChangeViewSet, basename='change')

urlpatterns = [
    path('', include(router.urls)),
]
