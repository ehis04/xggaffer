#!/usr/bin/env python
"""
Mock Fitbit Data Generator

Usage:
    cd backend
    python manage.py shell < ../mock_fitbit_data.py

Or run directly:
    python mock_fitbit_data.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from datetime import date, timedelta
from django.utils import timezone
from apps.users.models import User
from apps.integrations.models import FitbitToken, DailyActivitySummary

def create_mock_data(username='testuser', days=7):
    """Create mock Fitbit tokens and activity data for testing."""
    
    # Get or create test user
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"User '{username}' not found. Creating...")
        user = User.objects.create_user(
            username=username,
            email=f'{username}@test.com',
            password='testpass123'
        )
    
    # Create mock FitbitToken
    token, created = FitbitToken.objects.update_or_create(
        user=user,
        defaults={
            'fitbit_user_id': 'MOCK_FITBIT_123',
            'access_token': 'mock_access_token_' + timezone.now().isoformat(),
            'refresh_token': 'mock_refresh_token_xyz',
            'expires_at': timezone.now() + timedelta(days=30),
            'scope': 'activity heartrate profile',
            'last_synced_at': timezone.now(),
        }
    )
    print(f"{'Created' if created else 'Updated'} FitbitToken for {username}")
    
    # Create mock DailyActivitySummary for past N days
    today = date.today()
    for i in range(days):
        target_date = today - timedelta(days=i)
        
        # Generate realistic-looking mock data
        summary, created = DailyActivitySummary.objects.update_or_create(
            user=user,
            date=target_date,
            defaults={
                'steps': 5000 + (i * 1000) + (target_date.day * 100),  # Vary steps
                'calories_burned': 1800 + (i * 50),  # Vary calories
                'active_minutes': 20 + (i * 5),  # Vary active minutes
                'distance_km': 3.5 + (i * 0.2),  # Vary distance
                'resting_heart_rate': 58 + (i % 3),  # Vary resting HR
                'heart_rate_zones': {
                    'peak': 5 + (i % 10),
                    'cardio': 15 + (i % 5),
                    'fat_burn': 30 + (i % 3),
                    'out_of_range': 200 - (i * 10),
                }
            }
        )
        print(f"{'Created' if created else 'Updated'} DailyActivitySummary for {target_date}")
    
    print(f"\n✅ Mock data created successfully!")
    print(f"   User: {username}")
    print(f"   Days of data: {days}")
    print(f"\nTo test the API:")
    print(f"   GET /api/integrations/fitbit/status/")
    print(f"   GET /api/integrations/fitbit/activity/")
    print(f"   GET /api/integrations/fitbit/activity/?date={today}")

if __name__ == '__main__':
    username = sys.argv[1] if len(sys.argv) > 1 else 'testuser'
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    create_mock_data(username, days)