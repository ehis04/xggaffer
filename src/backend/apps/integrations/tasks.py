import logging
import requests
from datetime import date, timedelta

from django.utils import timezone
from django.conf import settings

from .models import FitbitToken, DailyActivitySummary
from apps.users.models import User

import base64

logger = logging.getLogger(__name__)

FITBIT_TOKEN_URL = "https://api.fitbit.com/oauth2/token"
FITBIT_ACTIVITY_URL = "https://api.fitbit.com/1/user/-/activities/date/{date}.json"
FITBIT_HEART_URL = "https://api.fitbit.com/1/user/-/activities/heart/date/{date}/1d.json"

def _refresh_fitbit_token(fitbit_token) -> bool:
    client_id = settings.FITBIT_CLIENT_ID
    client_secret = settings.FITBIT_CLIENT_SECRET
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    try:
        response = requests.post(
            FITBIT_TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": fitbit_token.refresh_token,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        
        fitbit_token.access_token = data["access_token"]
        fitbit_token.refresh_token = data["refresh_token"]
        fitbit_token.expires_at = timezone.now() + timedelta(seconds=data["expires_in"])
        fitbit_token.save(update_fields=["access_token", "refresh_token", "expires_at"])
        return True
    
    except Exception as e:
        logger.error(f"Failed to refresh Fitbit token for user {fitbit_token.user_id}: {e}")
        return False

def _get_valid_token(fitbit_token) -> str | None:
    if fitbit_token.is_expired:
        success = _refresh_fitbit_token(fitbit_token)
        if not success:
            return None
    return fitbit_token.access_token

def _fetch_activity(access_token: str, target_date: date) -> dict | None:
    url = FITBIT_ACTIVITY_URL.format(date=target_date.isoformat())
    
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch Fitbit activity data for date {target_date}: {e}")
        return None
    
def _fetch_heart_rate(access_token: str, target_date: date) -> dict | None:
    url = FITBIT_HEART_URL.format(date=target_date.isoformat())
    
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch Fitbit heart rate data for date {target_date}: {e}")
        return None
    
def _parse_and_save_session(user, target_date: date, activity_data:dict, heart_data: dict | None):
    summary = activity_data.get("summary", {})
    
    steps = summary.get("steps", 0)
    calories = summary.get("caloriesOut", 0)
    active_minutes = (summary.get("fairlyActiveMinutes", 0) + summary.get("veryActiveMinutes", 0))
    
    distance_km = 0.0
    for dist in summary.get("distances", []):
        if dist.get("activity") == "total":
            distance_km = dist.get("distance", 0.0)
            break
    
    resting_hr = None
    hr_zones = None
    
    if heart_data:
        hr_summary = (heart_data
        .get("activities-heart", [{}])[0]
        .get("value", {}))
        
        resting_hr = hr_summary.get("restingHeartRate")
        raw_zones = hr_summary.get("heartRateZones", [])
        
        if raw_zones:
            hr_zones = {
                zone["name"].lower().replace(" ", "_"): zone.get("minutes", 0)
                for zone in raw_zones}
            
        summary, created = DailyActivitySummary.objects.update_or_create(
            user=user,
            date=target_date,
            defaults={
                "steps": steps,
                "calories_burned": calories,
                "active_minutes": active_minutes,
                "distance_km": distance_km,
                "resting_heart_rate": resting_hr,
                "heart_rate_zones": hr_zones,
            },
        )
        
        action = "Created" if created else "Updated"
        
        logger.info(f"{action} DailyActivitySummary for user {user.username} on {target_date}")
        return summary

def sync_fitbit_for_user(user_id: int, target_date: date | None = None) -> str:
    if target_date is None:
        target_date = (timezone.now() - timedelta(days=1)).date()
            
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return f"User with id {user_id} does not exist."
    
    try:
        fitbit_token = user.fitbit_token
    except FitbitToken.DoesNotExist:
        return f"User {user_id} does not have a Fitbit token."
    
    access_token = _get_valid_token(fitbit_token)
    if not access_token:
        return f"Failed to refresh Fitbit token for user {user_id}."
    
    activity_data = _fetch_activity(access_token, target_date)
    if not activity_data:
        return f"Failed to fetch Fitbit activity data for user {user_id} on {target_date}."
    
    heart_data = _fetch_heart_rate(access_token, target_date)
    
    _parse_and_save_session(user, target_date, activity_data, heart_data)
    
    fitbit_token.last_synced_at = timezone.now()
    fitbit_token.save(update_fields=["last_synced_at"])
    
    return f"Successfully synced Fitbit data for user {user_id} on {target_date}."