from django.urls import path, include
from .Laws.views import CourseDetailView
from .learningTools.views import SubmitDrillView, SubmitScenarioView
from .progressTracking.views import RefereeDashboardView, MarkItemCompleteView
from .profile.views import CreateRefereeProfileView, RefereeProfileView

urlpatterns = [
    path('profile/create/', CreateRefereeProfileView.as_view(), name='create-referee-profile'),
    path('profile/', RefereeProfileView.as_view(), name='referee-profile'),
    path('courses/<int:law_number>/', CourseDetailView.as_view(), name='referee-course-detail'),
    path('scenario/', SubmitScenarioView.as_view(), name='referee-scenario-submit'),
    path('drill/', SubmitDrillView.as_view(), name='referee-drill-submit'),
    path('dashboard/', RefereeDashboardView.as_view(), name='referee-dashboard'),
    path('progress/complete/', MarkItemCompleteView.as_view(), name='referee-item-complete'),
    path('progress/scenario/', SubmitScenarioView.as_view(), name='referee-scenario-submit'),
    path('progress/drill/', SubmitDrillView.as_view(), name='referee-drill-submit'),
]
