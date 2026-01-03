#from django.urls import path, include
#from rest_framework.routers import DefaultRouter
#from .views import *

#router = DefaultRouter()
#router.register(r'teamsheets', TeamsheetViewSet, basename='teamsheet')
#router.register(r'players', TeamsheetPlayerViewSet, basename='teamsheetplayer')

#urlpatterns = [
#    path('', include(router.urls)),
#]

from django.urls import path
from .views import PredictMatchView, PredictBatchView, ModelInfoView

urlpatterns = [
    path('predict/', PredictMatchView.as_view(), name='predict-match'),
    path('predict/batch/', PredictBatchView.as_view(), name='predict-batch'),
    path('model-info/', ModelInfoView.as_view(), name='model-info'),
]