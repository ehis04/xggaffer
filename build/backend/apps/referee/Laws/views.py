from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import LawEdition, Law, LawClause, LawChange, KeyConcept, ParsingJob
from .serializers import (
    LawEditionListSerializer, LawEditionDetailSerializer,
    LawListSerializer, LawDetailSerializer,
    LawClauseSerializer, LawChangeSerializer,
    KeyConceptSerializer, KeyConceptDetailSerializer,
    ParsingJobSerializer,
)


class LawEditionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve law editions.
    GET /editions/          -> all editions (list)
    GET /editions/{id}/     -> single edition with laws list
    GET /editions/current/  -> the current active edition
    """
    queryset = LawEdition.objects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LawEditionDetailSerializer
        return LawEditionListSerializer

    @action(detail=False, methods=['get'])
    def current(self, request):
        edition = LawEdition.objects.filter(is_current=True).first()
        if not edition:
            return Response({'error': 'No current edition set.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = LawEditionDetailSerializer(edition)
        return Response(serializer.data)


class LawViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve laws.
    GET /laws/                     -> all laws (current edition by default)
    GET /laws/{id}/                -> full law detail with clauses
    GET /laws/{id}/clauses/        -> just the clauses for a law
    GET /laws/{id}/key_concepts/   -> key concepts for a law
    GET /laws/by_number/?number=5  -> look up by law number
    """
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description']

    def get_queryset(self):
        queryset = Law.objects.select_related('edition').prefetch_related(
            Prefetch('clauses', queryset=LawClause.objects.order_by('order').prefetch_related('key_concepts')),
            'key_concepts',
        )

        edition_id = self.request.query_params.get('edition')
        if edition_id:
            queryset = queryset.filter(edition_id=edition_id)
        else:
            current = LawEdition.objects.filter(is_current=True).first()
            if current:
                queryset = queryset.filter(edition=current)

        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty_level=difficulty)

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LawDetailSerializer
        return LawListSerializer

    @action(detail=False, methods=['get'])
    def by_number(self, request):
        number = request.query_params.get('number')
        if not number:
            return Response({'error': 'number parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        edition_id = request.query_params.get('edition')
        if edition_id:
            law = get_object_or_404(Law, number=number, edition_id=edition_id)
        else:
            current = LawEdition.objects.filter(is_current=True).first()
            if not current:
                return Response({'error': 'No current edition set.'}, status=status.HTTP_404_NOT_FOUND)
            law = get_object_or_404(Law, number=number, edition=current)

        serializer = LawDetailSerializer(law)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def clauses(self, request, pk=None):
        law = self.get_object()
        clauses = law.clauses.order_by('order').prefetch_related('key_concepts')
        serializer = LawClauseSerializer(clauses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def key_concepts(self, request, pk=None):
        law = self.get_object()
        concepts = law.key_concepts.all()
        critical_only = request.query_params.get('critical')
        if critical_only and critical_only.lower() == 'true':
            concepts = concepts.filter(is_critical=True)
        serializer = KeyConceptDetailSerializer(concepts, many=True)
        return Response(serializer.data)


class LawClauseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Retrieve individual clauses.
    GET /clauses/{id}/
    """
    queryset = LawClause.objects.select_related('law').prefetch_related('key_concepts').order_by('order')
    serializer_class = LawClauseSerializer


class LawChangeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List law changes between editions.
    GET /changes/?edition=1&law_number=5
    """
    serializer_class = LawChangeSerializer

    def get_queryset(self):
        queryset = LawChange.objects.select_related('edition')

        edition_id = self.request.query_params.get('edition')
        if edition_id:
            queryset = queryset.filter(edition_id=edition_id)

        law_number = self.request.query_params.get('law_number')
        if law_number:
            queryset = queryset.filter(law_number=law_number)

        change_type = self.request.query_params.get('change_type')
        if change_type:
            queryset = queryset.filter(change_type=change_type)

        return queryset


class KeyConceptViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Browse glossary of key concepts.
    GET /concepts/              -> all concepts
    GET /concepts/?critical=true
    GET /concepts/?law=5
    GET /concepts/?search=offside
    """
    serializer_class = KeyConceptDetailSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['term', 'definition']

    def get_queryset(self):
        queryset = KeyConcept.objects.select_related('law', 'clause')

        law_id = self.request.query_params.get('law')
        if law_id:
            queryset = queryset.filter(law_id=law_id)

        critical = self.request.query_params.get('critical')
        if critical and critical.lower() == 'true':
            queryset = queryset.filter(is_critical=True)

        return queryset.order_by('term')


class ParsingJobView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # add these imports

    def get(self, request):
        jobs = ParsingJob.objects.select_related('edition').order_by('-created_at')[:20]
        serializer = ParsingJobSerializer(jobs, many=True)
        return Response(serializer.data)

    def post(self, request):
        edition_id = request.data.get('edition_id')
        if not edition_id:
            return Response({'error': 'edition_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        edition = get_object_or_404(LawEdition, pk=edition_id)

        running = ParsingJob.objects.filter(edition=edition, status__in=['pending', 'processing']).first()
        if running:
            return Response(
                {'error': f'A parsing job is already running (id={running.id}).'},
                status=status.HTTP_409_CONFLICT,
            )

        job = ParsingJob.objects.create(edition=edition)

        # Handle uploaded file
        uploaded_file = request.FILES.get('pdf_file')
        if uploaded_file:
            import tempfile, os
            suffix = '.pdf'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            from apps.referee.Laws.tasks import parse_laws_pdf, _save_parsed_laws
            from django.utils import timezone

            job.status = 'processing'
            job.started_at = timezone.now()
            job.save()

            try:
                parsed = parse_laws_pdf(tmp_path)
                _save_parsed_laws(parsed, edition)
                job.status = 'completed'
                job.completed_at = timezone.now()
                job.parsed_data = {'laws_parsed': len(parsed)}
                job.save()
            except Exception as exc:
                job.status = 'failed'
                job.completed_at = timezone.now()
                job.error_message = str(exc)
                job.save()
            finally:
                os.unlink(tmp_path)  # clean up temp file

        else:
            # No file uploaded — run via URL in tasks (only works if URL is accessible)
            from apps.referee.Laws.tasks import run_parsing_job
            run_parsing_job(job.id)

        job.refresh_from_db()
        serializer = ParsingJobSerializer(job)
        return Response(serializer.data, status=status.HTTP_201_CREATED)