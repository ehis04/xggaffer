from django.urls import path
from .views import (
    FitbitConnectView,
    FitbitCallbackView,
    FitbitDisconnectView,
    FitbitStatusView,
    FitbitActivityView,
    FitbitManualSyncView,
    FitbitShareActivityView,
)

urlpatterns = [
    path("fitbit/connect/", FitbitConnectView.as_view(), name="fitbit-connect"),
    path("fitbit/callback/", FitbitCallbackView.as_view(), name="fitbit-callback"),
    path("fitbit/disconnect/", FitbitDisconnectView.as_view(), name="fitbit-disconnect"),
    path("fitbit/status/", FitbitStatusView.as_view(), name="fitbit-status"),
    path("fitbit/activity/", FitbitActivityView.as_view(), name="fitbit-activity"),
    path("fitbit/sync/", FitbitManualSyncView.as_view(), name="fitbit-sync"),
    path("fitbit/share/", FitbitShareActivityView.as_view(), name="fitbit-share"),
]