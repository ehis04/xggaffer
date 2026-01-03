"""
from celery import shared_task
from django.db.models import Q
from .services.google_calendar import GoogleCalendarService


@shared_task
def sync_event_to_google_calendar(event_id: int):
    from clubs.models import ClubEvent, ClubMembership
    from .models import GoogleCalendarIntegration
    
    try:
        event = ClubEvent.objects.select_related('club').get(id=event_id)
    except ClubEvent.DoesNotExist:
        return
    
    member_user_ids = ClubMembership.objects.filter(
        club=event.club,
        is_active=True
    ).values_list('user_id', flat=True)
    
    integrations = GoogleCalendarIntegration.objects.filter(
        user_id__in=member_user_ids,
        sync_enabled=True
    )
    
    for integration in integrations:
        service = GoogleCalendarService(integration)
        service.sync_event(event)


@shared_task
def sync_fixture_to_google_calendar(fixture_id: int):
    from clubs.models import Fixture, ClubMembership
    from .models import GoogleCalendarIntegration
    
    try:
        fixture = Fixture.objects.select_related('club').get(id=fixture_id)
    except Fixture.DoesNotExist:
        return
    
    member_user_ids = ClubMembership.objects.filter(
        club=fixture.club,
        is_active=True
    ).values_list('user_id', flat=True)
    
    integrations = GoogleCalendarIntegration.objects.filter(
        user_id__in=member_user_ids,
        sync_enabled=True,
        sync_fixtures=True
    )
    
    for integration in integrations:
        service = GoogleCalendarService(integration)
        service.sync_fixture(fixture)


@shared_task
def bulk_sync_club_calendar(club_id: int, user_id: int):
    from clubs.models import Club, ClubEvent, Fixture
    from .models import GoogleCalendarIntegration
    from django.utils import timezone
    
    try:
        integration = GoogleCalendarIntegration.objects.get(user_id=user_id)
        club = Club.objects.get(id=club_id)
    except (GoogleCalendarIntegration.DoesNotExist, Club.DoesNotExist):
        return
    
    service = GoogleCalendarService(integration)
    
    # Sync upcoming events
    upcoming_events = ClubEvent.objects.filter(
        club=club,
        start_datetime__gte=timezone.now()
    )
    for event in upcoming_events:
        service.sync_event(event)
    
    # Sync upcoming fixtures
    upcoming_fixtures = Fixture.objects.filter(
        club=club,
        date__gte=timezone.now().date()
    )
    for fixture in upcoming_fixtures:
        service.sync_fixture(fixture)
"""