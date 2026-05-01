"""
Root URL routing for the backend.

API route prefixes are registered and feature-specific routing is delegated to each Django app.
"""
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    path('internal/', include('apps.sync_pipeline.urls')),
    
    path('api/internal/', include('apps.internal.urls')),

    # Authentication and user management
    path('api/auth/', include('rest_framework.urls')),
    path('api/users/', include('apps.users.urls')),

    # Core coaching and team management
    path('api/coaching/', include('apps.coaching.urls')),
    path('api/teamsheets/', include('apps.teamsheets.urls')),
    path('api/clubs/', include('apps.clubs.urls')),
    path('api/players/', include('apps.players.urls')),

    # Predictions and football data
    path('predictions/', include('apps.predictions.urls')),
    path('api/predictions/', include('apps.predictions.urls')),
    path('api/playerdata/', include('apps.playerdata.urls')),
    path('api/livefootball/', include('apps.livefootball.urls')),

    # Community and learning modules
    path('api/community/', include('apps.community.urls')),
    path('api/articles/', include('apps.articles.urls')),
    #path('api/laws/', include('apps.laws.urls')),
    #path('api/quizzes/', include('apps.quizzes.urls')),
    path('api/referee/', include('apps.referee.urls')),
]
