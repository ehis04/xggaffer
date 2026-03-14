from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .Laws.views import (
    LawEditionViewSet, LawViewSet, LawClauseViewSet,
    LawChangeViewSet, KeyConceptViewSet, ParsingJobView,
)
from .learningTools.views import QuizViewSet, QuickDrillViewSet
from .progressTracking.views import (
    LearningDashboardView,
    LawProgressView,
    AllLawProgressView,
    MarkClauseReadView,
    QuizAttemptHistoryView,
    ToggleBookmarkView,
    MarkAttemptReviewedView,
    DrillAttemptHistoryView,
)

router = DefaultRouter()
router.register(r'editions', LawEditionViewSet, basename='edition')
router.register(r'laws', LawViewSet, basename='law')
router.register(r'clauses', LawClauseViewSet, basename='clause')
router.register(r'changes', LawChangeViewSet, basename='change')
router.register(r'concepts', KeyConceptViewSet, basename='concept')
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'drills', QuickDrillViewSet, basename='drill')

urlpatterns = [
    path('', include(router.urls)),
    path('parse/', ParsingJobView.as_view(), name='parse-pdf'),
    path('dashboard/', LearningDashboardView.as_view(), name='learning-dashboard'),

    # Law progress
    path('laws/', AllLawProgressView.as_view(), name='all-law-progress'),
    path('law/<int:law_id>/', LawProgressView.as_view(), name='law-progress'),
    path('law/<int:law_id>/clause/read/', MarkClauseReadView.as_view(), name='mark-clause-read'),

    # Attempt history
    path('attempts/quizzes/', QuizAttemptHistoryView.as_view(), name='quiz-attempt-history'),
    path('attempts/quizzes/<int:attempt_id>/bookmark/', ToggleBookmarkView.as_view(), name='toggle-bookmark'),
    path('attempts/quizzes/<int:attempt_id>/reviewed/', MarkAttemptReviewedView.as_view(), name='mark-reviewed'),
    path('attempts/drills/', DrillAttemptHistoryView.as_view(), name='drill-attempt-history'),
]