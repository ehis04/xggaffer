from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, F
from django.db import transaction
import logging
import math

logger = logging.getLogger(__name__)


def calculate_post_interest_scores():
    from .models import Post, PostUserInterestScore, UserInterestProfile
    from apps.users.models import User
    from datetime import timedelta

    start_time = timezone.now()

    recent_posts = Post.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7),
        moderation_status='OK',
        visibility='PB'
    ).prefetch_related('post_tags__hashtag')

    users_with_profiles = User.objects.filter(
        interest_profile__isnull=False
    ).prefetch_related(
        'interest_profile__hashtag_interests__hashtag',
        'interest_profile__author_interests__author'
    )

    scores_created = 0

    for user in users_with_profiles:
        profile = user.interest_profile

        hashtag_interests = {
            hi.hashtag.body: hi.score for hi in profile.hashtag_interests.all()
        }
        author_profiles = {
            ai.author.id: ai.score for ai in profile.author_interests.all()
        }

        for post in recent_posts:
            if post.author_id == user.id:
                continue

            hashtag_score = 0.0
            for post_tag in post.post_tags.all():
                hashtag_body = post_tag.hashtag.body
                if hashtag_body in hashtag_interests:
                    hashtag_score = max(hashtag_score, hashtag_interests[hashtag_body])

            author_score = author_profiles.get(post.author_id, 0.0)

            combined_score = max(hashtag_score, author_score)

            score_obj, created = PostUserInterestScore.objects.update_or_create(
                user=user,
                post=post,
                defaults={
                    'hashtag_interest_score': hashtag_score,
                    'author_interest_score': author_score,
                    'combined_interest_score': combined_score,
                }
            )

            if created:
                scores_created += 1

        old_scores_deleted = PostUserInterestScore.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=7),
        ).delete()[0]

        duration = timezone.now() - start_time
        logger.info(f"Calculated {scores_created} scores, deleted {old_scores_deleted} old scores in {duration.total_seconds():.2f} seconds")

        return f"Created {scores_created} scores, deleted {old_scores_deleted} old scores"


@shared_task(name='apps.community.tasks.update_user_interest_profiles_task')
def update_user_interest_profiles_task():
    from .models import UserInterestProfile
    from apps.users.models import User

    start_time = timezone.now()
    updated_count = 0

    batch_size = 50
    users = User.objects.all()

    for i in range(0, users.count(), batch_size):
        batch = users[i:i + batch_size]
        for user in batch:
            try:
                profile, created = UserInterestProfile.objects.get_or_create(user=user)
                _update_single_user_profile(user, profile)
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update profile for user {user.id}: {e}")

    duration = timezone.now() - start_time
    logger.info(f"Updated {updated_count} user profiles in {duration.total_seconds():.2f} seconds")

    calculate_post_interest_scores()

    return f"Updated {updated_count} profiles and calculated interest scores"


def _update_single_user_profile(user, profile):
    from .models import UserHashtagInterest, UserAuthorInterest, Like, Comment, Post
    from django.contrib.contenttypes.models import ContentType

    DECAY_HALF_LIFE_DAYS = 7
    LOOKBACK_DAYS = 30

    LIKE_WEIGHT = 1.0
    COMMENT_WEIGHT = 3.0
    REPLY_WEIGHT = 2.0

    cutoff_date = timezone.now() - timedelta(days=LOOKBACK_DAYS)

    with transaction.atomic():
        _update_hashtag_interests(user, profile, cutoff_date, DECAY_HALF_LIFE_DAYS, LIKE_WEIGHT, COMMENT_WEIGHT, REPLY_WEIGHT)
        _update_author_interests(user, profile, cutoff_date, DECAY_HALF_LIFE_DAYS, LIKE_WEIGHT, COMMENT_WEIGHT, REPLY_WEIGHT)
        _cleanup_interests(profile)
    profile.save()


def _update_hashtag_interests(user, profile, cutoff_date, half_life_days, like_weight, comment_weight, reply_weight):
    from .models import UserHashtagInterest, Like, Comment, Post
    from django.contrib.contenttypes.models import ContentType

    hashtag_scores = {}

    post_content_type = ContentType.objects.get_for_model(Post)
    liked_posts_with_tags = (
        Like.objects.filter(
            user=user,
            content_type=post_content_type,
            created_at__gte=cutoff_date
        )
        .select_related('content_object')
        .prefetch_related('content_object__post_tags__hashtag')
    )

    for like in liked_posts_with_tags:
        post = like.content_object
        if not post:
            continue

        age_days = (timezone.now() - like.created_at).days
        decay_factor = _calculate_decay(age_days, half_life_days)
        score = like_weight * decay_factor

        for post_tag in post.post_tags.all():
            hashtag = post_tag.hashtag.body
            hashtag_scores[hashtag] = hashtag_scores.get(hashtag, 0) + score

        user_comments = (
            Comment.objects.filter(
                author=user,
                created_at__gte=cutoff_date,
                post__isnull=False
            )
            .select_related('post')
            .prefetch_related('post__post_tags__hashtag')
        )

        for comment in user_comments:
            if not comment.post:
                continue

            age_days = (timezone.now() - comment.created_at).days
            decay_factor = _calculate_decay(age_days, half_life_days)

            weight = reply_weight if comment.parent_id else comment_weight
            score = weight * decay_factor

            for post_tag in comment.post.post_tags.all():
                hashtag = post_tag.hashtag.body
                hashtag_scores[hashtag] = hashtag_scores.get(hashtag, 0) + score

        from .models import HashTag
        for hashtag_body, score in hashtag_scores.items():
            try:
                hashtag = HashTag.objects.get(body=hashtag_body)
                interest, created = UserHashtagInterest.objects.get_or_create(
                    profile=profile,
                    hashtag=hashtag,
                    defaults={'score': score, 'last_interaction': timezone.now()}
                )
                if not created:
                    interest.score = 0.7 * interest.score + 0.3 * score
                    interest.last_interaction = timezone.now()
                    interest.save()
            except Hashtag.DoesNotExist:
                continue


def _update_author_interests(user, profile, cutoff_date, half_life_days, like_weight, comment_weight, reply_weight):
    from .models import UserAuthorInterest, Like, Comment, Post
    from django.contrib.contenttypes.models import ContentType

    author_scores = {}

    post_content_type = ContentType.objects.get_for_model(Post)
    liked_posts = (
        Like.objects.filter(
            user=user,
            content_type=post_content_type,
            created_at__gte=cutoff_date
        )
        .select_related('content_object__author')
    )

    for like in liked_posts:
        post = like.content_object
        if not post or post.author_id == user.id:
            continue

        age_days = (timezone.now() - like.created_at).days
        decay_factor = _calculate_decay(age_days, half_life_days)
        score = like_weight * decay_factor

        author_id = post.author_id
        author_scores[author_id] = author_scores.get(author_id, 0) + score

    user_comments = (
        Comment.objects.filter(
            author=user,
            created_at__gte=cutoff_date,
            post__isnull=False
        )
        .select_related('post__author')
    )

    for comment in user_comments:
        if not comment.post or comment.post.author_id == user.id:
            continue

        age_days = (timezone.now() - comment.created_at).days
        decay_factor = _calculate_decay(age_days, half_life_days)

        weight = reply_weight if comment.parent_id else comment_weight
        score = weight * decay_factor

        author_id = comment.post.author_id
        author_scores[author_id] = author_scores.get(author_id, 0) + score

    from apps.users.models import User
    for author_id, score in author_scores.items():
        try:
            author = User.objects.get(id=author_id)
            interest, created = UserAuthorInterest.objects.get_or_create(
                profile=profile,
                author=author,
                defaults={'score': score, 'last_interaction': timezone.now()}
            )
            if not created:
                interest.score = 0.7 * interest.score + 0.3 * score
                interest.last_interaction = timezone.now()
                interest.save()
        except User.DoesNotExist:
            continue


def _calculate_decay(age_days, half_life_days):
    return math.exp(-math.log(2) * age_days / half_life_days)


def _cleanup_interests(profile):
    from .models import UserHashtagInterest, UserAuthorInterest

    MIN_SCORE = 0.1
    MAX_AGE_DAYS = 90

    old_date = timezone.now() - timedelta(days=MAX_AGE_DAYS)

    UserHashtagInterest.objects.filter(
        Q(profile=profile) &
        (Q(score__lt=MIN_SCORE) | Q(last_interaction__lt=old_date))
    ).delete()

    UserAuthorInterest.objects.filter(
        Q(profile=profile) &
        (Q(score__lt=MIN_SCORE) | Q(last_interaction__lt=old_date))
    ).delete()
