"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('rest_framework.urls')),
    path('api/teamsheets/', include('apps.teamsheets.urls')),
    path('api/predictions/', include('apps.predictions.urls')),
    path('api/community/', include('apps.community.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/coaching/', include('apps.coaching.urls')),
    path('api/players/', include('apps.players.urls')),
    path('api/clubs/', include('apps.clubs.urls')),
    path('api/tactics/', include('apps.tactics.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/playerdata/', include('apps.playerdata.urls')),
    path('api/livefootball/', include('apps.livefootball.urls')),
    path('api/referee/', include('apps.referee.urls')),
]
