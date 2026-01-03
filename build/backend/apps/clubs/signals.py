"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ClubEvent, Fixture


@receiver(post_save, sender=ClubEvent)
def sync_event_on_save(sender, instance, **kwargs):
    from integrations.tasks import sync_event_to_google_calendar
    # Delay to avoid blocking the request
    sync_event_to_google_calendar.delay(instance.id)


@receiver(post_save, sender=Fixture)
def sync_fixture_on_save(sender, instance, **kwargs):
    from integrations.tasks import sync_fixture_to_google_calendar
    sync_fixture_to_google_calendar.delay(instance.id)


@receiver(post_delete, sender=ClubEvent)
def delete_event_from_google(sender, instance, **kwargs):
    if instance.google_event_id:
        from integrations.tasks import delete_google_event
        delete_google_event.delay(
            instance.club_id,
            instance.google_event_id
        )
"""