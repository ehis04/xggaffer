from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.coaching.coachProfile.views import CreateCoachProfileView, CoachProfileView

urlpatterns = [
    path('profile/create/', CreateCoachProfileView.as_view(), name='create-coach-profile'),
    path('profile/', CoachProfileView.as_view(), name='coach-profile'),
]