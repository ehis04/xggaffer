from django.shortcuts import render

import base64
import secrets
import requests
from datetime import timedelta, date

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .tasks import sync_fitbit_for_user

from .models import FitbitToken, DailyActivitySummary
from .serializers import FitbitTokenSerializer, DailyActivitySerializer

# Create your views here.

FITBIT_AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
FITBIT_TOKEN_URL = "https://api.fitbit.com/oauth2/token"
FITBIT_SCOPES = "activity heartrate profile"

class FitbitConnectView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        state = secrets.token_urlsafe(16)
        request.session["fitbit_oauth_state"] = state
        
        params = {
            "response_type": "code",
            "client_id": settings.FITBIT_CLIENT_ID,
            "redirect_uri": settings.FITBIT_REDIRECT_URL,
            "scope": FITBIT_SCOPES,
            "state": state,
        }
        
        auth_url = (
            f"{FITBIT_AUTH_URL}?"
            + "&".join(f"{k}={v}" for k, v in params.items())
        )
        return redirect(auth_url)

class FitbitCallbackView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")
        
        if error:
            return Response({"detail": f"Fitbit authorisation failed: {error}"}, status=status.HTTP_400_BAD_REQUEST)
        
        expected_state = request.session.pop("fitbit_oauth_state", None)
        if not state or state != expected_state:
            return Response({"detail": "Invalid state parameter"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not code:
            return Response({"detail": "Authorisation code not provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        credentials = base64.b64encode(f"{settings.FITBIT_CLIENT_ID}:{settings.FITBIT_CLIENT_SECRET}".encode()).decode()
        
        try:
            response = requests.post(
                FITBIT_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.FITBIT_REDIRECT_URL,
                },
                timeout=10,
            )
            response.raise_for_status()
            token_data = response.json()
        except requests.RequestException as e:
            return Response({"detail": f"Failed to exchange code for token: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)
        
        expires_at = timezone.now() + timedelta(seconds=token_data["expires_in"])
        
        FitbitToken.objects.update_or_create(
            user=request.user,
            defaults={
                "fitbit_user_id": token_data.get("user_id", ""),
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_at": expires_at,
                "scope": token_data.get("scope", ""),
            }
        )
        
        frontend_profile_url = getattr(
            settings, "FRONTEND_PROFILE_URL", "http://localhost:3000/profile"
        )
        return redirect(f"{frontend_profile_url}?fitbit=connected")
    
class FitbitDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        deleted_count, _ = FitbitToken.objects.filter(user=request.user).delete()
        if deleted_count:
            return Response({"detail": "Fitbit account disconnected."})
        return Response(
            {"detail": "No Fitbit account connected."},
            status=status.HTTP_404_NOT_FOUND,
        )

class FitbitStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            token = request.user.fitbit_token
            serializer = DailyActivitySerializer(token)
            return Response({"connected": True, **serializer.data})
        except FitbitToken.DoesNotExist:
            return Response({"connected": False})
        
class FitbitActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        single_date_str = request.query_params.get("date")

        if single_date_str:
            try:
                from datetime import date as date_type
                target = date_type.fromisoformat(single_date_str)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                snapshot = DailyActivitySummary.objects.get(user=request.user, date=target)
                return Response(DailyActivitySerializer(snapshot).data)
            except DailyActivitySummary.DoesNotExist:
                return Response(
                    {"detail": f"No activity data for {target}."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Default: last N days
        try:
            days = int(request.query_params.get("days", 7))
            days = min(max(days, 1), 90)  # clamp between 1–90
        except ValueError:
            days = 7

        cutoff = timezone.now().date() - timedelta(days=days)
        snapshots = DailyActivitySummary.objects.filter(
            user=request.user,
            date__gte=cutoff,
        ).order_by("-date")

        return Response({
            "days_requested": days,
            "count": snapshots.count(),
            "results": DailyActivitySerializer(snapshots, many=True).data,
        })


class FitbitManualSyncView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check they actually have a connected account
        if not hasattr(request.user, "fitbit_token"):
            return Response(
                {"detail": "No Fitbit account connected. Visit /integrations/fitbit/connect/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        date_str = request.data.get("date")
        target_date = None

        if date_str:
            try:
                from datetime import date as date_type
                target_date = date_type.fromisoformat(date_str)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        result = sync_fitbit_for_user(request.user.id, target_date)
        return Response({"detail": result}, status=status.HTTP_200_OK)


class FitbitShareActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        date_str = request.data.get("date")

        if date_str:
            try:
                from datetime import date as date_type
                target_date = date_type.fromisoformat(date_str)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = (timezone.now() - timedelta(days=1)).date()

        try:
            snapshot = DailyActivitySummary.objects.get(
                user=request.user, date=target_date
            )
        except DailyActivitySummary.DoesNotExist:
            return Response(
                {"detail": f"No activity data for {target_date}. Try syncing first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Use the model's helper to generate post text, then create the Post.
        # This triggers your existing sync_post_hashtags signal automatically.
        from apps.community.models import Post
        post = Post.objects.create(
            author=request.user,
            text_body=snapshot.as_post_text(),
        )

        return Response(
            {
                "detail": "Activity shared as a post.",
                "post_id": post.id,
                "text_body": post.text_body,
            },
            status=status.HTTP_201_CREATED,
        )