from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from apps.users.models import UserProfile
from apps.referee.Laws.models import Law, CourseItem

from .models import (
    UserCourseProgress,
    UserItemProgress,
    StudyStreak,
    PerformanceScore,
)

# Returns the user's most recently accessed active course
def get_active_course(user_profile: UserProfile) -> UserCourseProgress | None:
    return (
        UserCourseProgress.objects
        .filter(user_profile=user_profile, status=UserCourseProgress.STATUS_ACTIVE)
        .select_related('law')
        .order_by('-last_accessed')
        .first()
    )

# Returns progress rows for all laws, creating unsaved placeholder progress objects where no database row exists yet
def get_all_courses(user_profile: UserProfile) -> list[UserCourseProgress]:
    laws = Law.objects.all()

    progress_map: dict[int, UserCourseProgress] = {
        p.law_id: p
        for p in UserCourseProgress.objects
        .filter(user_profile=user_profile)
        .select_related('law')
    }

    result = []
    for law in laws:
        if law.pk in progress_map:
            result.append(progress_map[law.pk])
        else:
            total = CourseItem.objects.filter(section__law=law).count()
            stub  = UserCourseProgress(
                user_profile=user_profile,
                law=law,
                status=UserCourseProgress.STATUS_ACTIVE if law.law_number == 1 else UserCourseProgress.STATUS_LOCKED,
                clauses_read=0,
                total_clauses=total,
            )
            result.append(stub)

    return result

# Gets or creates the user's study streak record
def get_streak(user_profile: UserProfile) -> StudyStreak:
    streak, _ = StudyStreak.objects.get_or_create(user_profile=user_profile)
    return streak

# Gets or creates the user's performance score record
def get_performance(user_profile: UserProfile) -> PerformanceScore:
    perf, _ = PerformanceScore.objects.get_or_create(user_profile=user_profile)
    return perf

# Returns the ids of completed course items for a user within a specific law
def get_completed_item_ids(user_profile: UserProfile, law: Law) -> set[int]:
    return set(
        UserItemProgress.objects.filter(
            user_profile=user_profile,
            item__section__law=law,
            completed=True,
        ).values_list('item_id', flat=True)
    )

# Returns the next incomplete item id for a user within a specific law
def get_active_item_id(user_profile: UserProfile, law: Law) -> int | None:
    completed_ids = get_completed_item_ids(user_profile, law)

    for section in law.sections.prefetch_related('items').order_by('order'):
        for item in section.items.order_by('order'):
            if item.pk not in completed_ids:
                return item.pk

    return None

# Marks a course item as completed and refreshes course progress, streaks, and performance scores
@transaction.atomic
def mark_item_complete(user_profile: UserProfile, item_id: int) -> UserItemProgress:
    item = CourseItem.objects.select_related('section__law').get(pk=item_id)
    now  = timezone.now()

    progress, _ = UserItemProgress.objects.get_or_create(
        user_profile=user_profile,
        item=item,
    )

    if not progress.completed:
        progress.completed    = True
        progress.completed_at = now
        progress.save(update_fields=['completed', 'completed_at'])

    _refresh_course_progress(user_profile, item.section.law, now)
    _update_streak(user_profile)
    _recompute_performance(user_profile)

    return progress

# Saves a user's scenario answer and completes the item only when the selected answer is correct
@transaction.atomic
def submit_scenario(
    user_profile: UserProfile,
    item_id: int,
    selected_id: str,
) -> UserItemProgress:
    item    = CourseItem.objects.select_related('section__law').get(
                  pk=item_id, item_type='scenario')
    correct = (selected_id == item.scenario_correct_id)

    progress, _ = UserItemProgress.objects.get_or_create(
        user_profile=user_profile,
        item=item,
    )

    progress.scenario_selected_id = selected_id
    progress.scenario_correct     = correct

    if correct and not progress.completed:
        progress.completed    = True
        progress.completed_at = timezone.now()

    progress.save()

    if correct:
        _refresh_course_progress(user_profile, item.section.law, timezone.now())
        _update_streak(user_profile)
        _recompute_performance(user_profile)

    return progress


# Saves a user's drill answers and marks the drill item as completed
@transaction.atomic
def submit_drill(
    user_profile: UserProfile,
    item_id: int,
    answers: dict,
) -> UserItemProgress:
    item = CourseItem.objects.select_related('section__law').get(
               pk=item_id, item_type='drill')

    progress, _ = UserItemProgress.objects.get_or_create(
        user_profile=user_profile,
        item=item,
    )

    progress.drill_answers   = answers
    progress.drill_submitted = True

    if not progress.completed:
        progress.completed    = True
        progress.completed_at = timezone.now()

    progress.save()

    _refresh_course_progress(user_profile, item.section.law, timezone.now())
    _update_streak(user_profile)
    _recompute_performance(user_profile)

    return progress

# Recalculates a user's progress totals and status for one law
def _refresh_course_progress(
    user_profile: UserProfile,
    law: Law,
    now,
) -> None:
    total = CourseItem.objects.filter(section__law=law).count()
    done  = UserItemProgress.objects.filter(
        user_profile=user_profile,
        item__section__law=law,
        completed=True,
    ).count()

    cp, _ = UserCourseProgress.objects.get_or_create(
        user_profile=user_profile,
        law=law,
        defaults={'total_clauses': total},
    )

    cp.clauses_read  = done
    cp.total_clauses = total
    cp.last_accessed = now

    if cp.status == UserCourseProgress.STATUS_LOCKED:
        cp.status     = UserCourseProgress.STATUS_ACTIVE
        cp.started_at = now

    if done >= total and total > 0:
        cp.status       = UserCourseProgress.STATUS_COMPLETED
        cp.completed_at = now

    cp.save()

# Updates the user's study streak based on the dates they have studied
def _update_streak(user_profile: UserProfile) -> None:
    streak, _ = StudyStreak.objects.get_or_create(user_profile=user_profile)
    today     = date.today()

    dates_set = set(streak.studied_dates or [])
    dates_set.add(today)
    sorted_dates = sorted(dates_set, reverse=True)

    current = 0
    check   = today
    for d in sorted_dates:
        if d == check:
            current += 1
            check   -= timedelta(days=1)
        elif d < check:
            break

    streak.studied_dates  = sorted_dates
    streak.current_streak = current
    streak.last_updated   = today
    streak.save()

# Recalculates the user's percentage scores for each course type and their overall performance score
def _recompute_performance(user_profile: UserProfile) -> None:
    perf, _ = PerformanceScore.objects.get_or_create(user_profile=user_profile)

    def _score(item_type: str) -> int | None:
        total = CourseItem.objects.filter(item_type=item_type).count()
        if total == 0:
            return None
        done = UserItemProgress.objects.filter(
            user_profile=user_profile,
            item__item_type=item_type,
            completed=True,
        ).count()
        if done == 0:
            return None
        return round((done / total) * 100)

    perf.clause_score   = _score('clause')
    perf.scenario_score = _score('scenario')
    perf.drill_score    = _score('drill')
    perf.quiz_score     = _score('quiz')

    scores = [
        s for s in [
            perf.clause_score,
            perf.scenario_score,
            perf.drill_score,
            perf.quiz_score,
        ]
        if s is not None
    ]
    perf.overall_score = round(sum(scores) / len(scores)) if scores else 0
    perf.save()