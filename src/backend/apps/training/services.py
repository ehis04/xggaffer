from apps.clubs.models import ClubEvent

from .models import TrainingSession


def sync_session_calendar_event(session: TrainingSession) -> TrainingSession:
    if session.status == TrainingSession.Status.CANCELLED:
        if session.calendar_event_id:
            session.calendar_event.delete()
            session.calendar_event = None
            session.save(update_fields=['calendar_event', 'updated_at'])
        return session

    if session.status not in {TrainingSession.Status.PUBLISHED, TrainingSession.Status.COMPLETED}:
        return session

    event = session.calendar_event or ClubEvent(
        club=session.club,
        created_by=session.created_by,
        event_type=ClubEvent.EventType.TRAINING,
        source_type=ClubEvent.SourceType.MANUAL,
    )

    event.title = session.title
    event.description = session.main_objective or session.notes
    event.start_datetime = session.start_datetime
    event.end_datetime = session.end_datetime
    event.location = session.location
    event.is_all_day = False
    event.is_mandatory = session.is_mandatory
    event.save()

    if session.calendar_event_id != event.id:
        session.calendar_event = event
        session.save(update_fields=['calendar_event', 'updated_at'])

    return session

