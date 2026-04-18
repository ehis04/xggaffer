from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    PostSerializer,
    ExplorePostSerializer,
    CommentSerializer,
    CommentListSerializer,
    CommentResponseSerializer,
    NotificationListSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError
from .models import Post, Visibility, ModerationStatus, PostView, Comment, Like, ContentType, Notification
from apps.users.models import User, UserProfile, Follow
from rest_framework.generics import CreateAPIView, RetrieveAPIView, RetrieveUpdateAPIView, ListAPIView, RetrieveUpdateDestroyAPIView
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from django.utils.dateparse import parse_date
from django.db.models import Q, F, FloatField, IntegerField, ExpressionWrapper
from django.db.models.expressions import RawSQL
from django.db import transaction
from django.contrib.contenttypes.prefetch import GenericPrefetch

# Create New Post

class CreateNewPostView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

# Get single posts
class GetPostView(RetrieveAPIView):
    queryset = (
        Post.objects
        .select_related("author")
        .filter(moderation_status=ModerationStatus.OK, visibility=Visibility.PUBLIC)
    )
    serializer_class = ExplorePostSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "post_id"
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(visibility=Visibility.PUBLIC)

class GetCommentView(RetrieveAPIView):
    queryset = (
        Comment.objects
        .select_related("author")
        .filter(moderation_status=ModerationStatus.OK)
    )
    serializer_class = CommentListSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "comment_id"
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset
    

# Update own posts, get, and delete

class UserPostView(RetrieveUpdateDestroyAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "post_id"
    queryset = Post.objects.none()
    
    def get_queryset(self):
        return (
            Post.objects.select_related("author").filter(author=self.request.user)
        )
        
    @transaction.atomic
    def perform_update(self, serializer):
        serializer.save(author=self.request.user)
    
    @transaction.atomic
    def perform_destroy(self, instance):
        instance.delete()

# List Posts
class ExplorePagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page-size'
    max_page_size = 50
    page_query_param = 'page'

class ExplorePostsView(ListAPIView):
    serializer_class = ExplorePostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ExplorePagination
    
    def get_queryset(self):
        user = self.request.user
        
        # Get ids of the posts the user has already viewed
        viewed_post_ids = PostView.objects.filter(user=user).values_list('post_id', flat=True)
        
        queryset = Post.objects.filter(
            moderation_status=ModerationStatus.OK,
            visibility=Visibility.PUBLIC
        ).exclude(Q(id__in=viewed_post_ids)
        ).select_related(
            'author', 'author__profile'
        ).prefetch_related(
            'post_tags__hashtag',
            'comments__author'
        )
        
        queryset = self._apply_filters(queryset)
        queryset = self._apply_ordering(queryset)
        
        return queryset
    
    def _apply_filters(self, queryset):
        hashtag = self.request.query_params.get('hashtag')
        if hashtag:
            hashtag_clean = hashtag.lower().lstrip('#')
            queryset = queryset.filter(post_tags__hashtag__body=hashtag_clean)
            
        hashtags = self.request.query_params.get('hashtags')
        if hashtags:
            hashtag_list = [tag.strip().lower().lstrip('#') for tag in hashtags.split(',')]
            queryset = queryset.filter(post_tags__hashtag__body__in=hashtag_list)
        
        min_likes = self.request.query_params.get('min_likes')
        if min_likes:
            try:
                queryset = queryset.filter(no_of_likes__gte=int(min_likes))
            except ValueError:
                pass
        
        max_likes = self.request.query_params.get('max_likes')
        if max_likes:
            try:
                queryset = queryset.filter(no_of_likes__lte=int(max_likes))
            except ValueError:
                pass
        
        min_comments = self.request.query_params.get('min_comments')
        if min_comments:
            try:
                queryset = queryset.filter(no_of_comments__gte=int(min_comments))
            except ValueError:
                pass
        
        max_comments = self.request.query_params.get('max_comments')
        if max_comments:
            try:
                queryset = queryset.filter(no_of_comments__lte=int(max_comments))
            except ValueError:
                pass
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(text_body__icontains=search)
        
        author = self.request.query_params.get('author')
        if author:
            queryset = queryset.filter(author__username=author)
            
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            try:
                from_date = parse_date(date_from)
                if from_date:
                    queryset = queryset.filter(created_at__date__gte=from_date)
            except ValueError:
                pass
        if date_to:
            try:
                to_date = parse_date(date_to)
                if to_date:
                    queryset = queryset.filter(created_at__date__lte=to_date)
            except ValueError:
                pass
        
        has_attachments = self.request.query_params.get('has_attachments')
        if has_attachments and has_attachments.lower() == 'true':
            queryset = queryset.filter(attachments_count__gt=0)
        elif has_attachments and has_attachments.lower() == 'false':
            queryset = queryset.filter(attachments_count=0)
        
        return queryset
    
    def _apply_ordering(self, queryset):
        order_by = self.request.query_params.get('order_by', 'likes')
        
        if order_by == 'recent':
            return queryset.order_by('-created_at')
        elif order_by == 'ranked':
            # --config--
            half_life_hours = 24
            
            # Popularity = likes + 2*comments
            popularity_expr = ExpressionWrapper(
                F('no_of_likes') + 2 * F('no_of_comments'),
                output_field=FloatField(),
            )
            
            # MySQL: age in hours and exponential decay for recncy
            age_hours_sql = RawSQL("EXTRACT(EPOCH FROM (NOW() - community_post.created_at)) / 3600", [])
            recency_sql = RawSQL("EXP(-LN(2) * EXTRACT(EPOCH FROM (NOW() - community_post.created_at)) / 3600 / %s)", [half_life_hours])
            
            # scale recency so it competes with popularity
            recency_scaled_expr = ExpressionWrapper(
                recency_sql * 100.0,
                output_field=FloatField(),
            )
            
            # Final ranked score: 0.7 popularity + 0.3 recency
            ranked_score_expr = ExpressionWrapper(
                0.7 * popularity_expr + 0.3 * recency_scaled_expr,
                output_field=FloatField(),
            )
            
            return queryset.annotate(popularity=popularity_expr, recency_scaled=recency_scaled_expr, ranked_score=ranked_score_expr)\
                .order_by('-popularity', '-created_at')
        elif order_by == 'oldest':
            return queryset.order_by('created_at')
        elif order_by == 'comments':
            return queryset.order_by('-no_of_comments', '-created_at')
        elif order_by == 'comments_asc':
            return queryset.order_by('no_of_comments', 'created_at')
        elif order_by == 'likes_asc':
            return queryset.order_by('no_of_likes', 'created_at')
        elif order_by == 'trending':
            from django.utils import timezone
            from datetime import timedelta
            
            seven_days_ago = timezone.now() - timedelta(days=7)
            return queryset.extra(select={
                'trending_score': '''
                    CASE WHEN community_post.created_at > %s 
                        THEN community_post.no_of_likes * 2 + community_post.no_of_comments * 3
                        ELSE community_post.no_of_likes + community_post.no_of_comments
                    END'''
            },
            select_params=[seven_days_ago]
            ).order_by('-trending_score', '-created_at')
        else:
            return queryset.order_by('-no_of_likes', '-created_at')
        
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        if hasattr(response, 'data') and isinstance(response.data, dict):
            response.data['filters_applied'] = {
                'hashtag': request.query_params.get('hashtag'),
                'search': request.query_params.get('search'),
                'order_by': request.query_params.get('order_by', 'likes'),
                'min_likes': request.query_params.get('min_likes'),
                'author': request.query_params.get('author'),
            }
            
            if response.data['count'] == 0:
                response.data['suggestion'] = 'Try adjusting your filters.'
        
        return response

class FollowingPostsView(ListAPIView):
    serializer_class = ExplorePostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ExplorePagination
    
    def get_queryset(self):
        user = self.request.user
        
        try:
            user_profile = user.profile
        except UserProfile.DoesNotExist:
            return Post.objects.none()
        
        followed_users_ids = Follow.objects.filter(follower=user_profile).values_list('following__user_id', flat=True)
        
        if not followed_users_ids:
            return Post.objects.none()
        
        viewed_post_ids = PostView.objects.filter(user=user).values_list('post_id', flat=True)
        
        queryset = Post.objects.filter(
            moderation_status=ModerationStatus.OK,
            visibility__in=[Visibility.PUBLIC, Visibility.FOLLOWERS],
            author_id__in=followed_users_ids
        ).exclude(Q(id__in=viewed_post_ids)
        ).select_related(
            'author', 'author__profile'
        ).prefetch_related(
            'post_tags__hashtag',
            'comments__author'
        ).order_by('-created_at')
        
        return queryset


class HashtagPostsView(ListAPIView):

    serializer_class = ExplorePostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ExplorePagination

    def get_queryset(self):
        hashtag_raw = self.request.query_params.get("hashtag")
        if not hashtag_raw or not str(hashtag_raw).strip():
            raise ValidationError({"hashtag": "This query parameter is required."})
        hashtag_clean = str(hashtag_raw).strip().lower().lstrip("#")

        followed_user_ids = []
        try:
            user_profile = self.request.user.profile
            followed_user_ids = list(
                Follow.objects.filter(follower=user_profile).values_list(
                    "following__user_id", flat=True
                )
            )
        except UserProfile.DoesNotExist:
            pass

        visibility_q = Q(visibility=Visibility.PUBLIC)
        if followed_user_ids:
            visibility_q |= Q(
                author_id__in=followed_user_ids,
                visibility=Visibility.FOLLOWERS,
            )

        return (
            Post.objects.filter(
                moderation_status=ModerationStatus.OK,
            )
            .filter(visibility_q)
            .filter(post_tags__hashtag__body=hashtag_clean)
            .distinct()
            .select_related("author", "author__profile")
            .prefetch_related("post_tags__hashtag", "comments__author")
            .order_by("-created_at")
        )

class UserPostsListView(ListAPIView):
    serializer_class = ExplorePostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ExplorePagination
    
    def get_queryset(self):
        username = self.kwargs["username"]
        
        if self.request.user.username == username:
            return Post.objects.filter(
                author__username=username,
                moderation_status=ModerationStatus.OK
            ).select_related("author", "author__profile").prefetch_related("post_tags__hashtag").order_by("-created_at")
            
        return Post.objects.filter(
            author__username=username,
            moderation_status=ModerationStatus.OK,
            visibility=Visibility.PUBLIC
        ).select_related("author", "author__profile").prefetch_related("post_tags__hashtag").order_by("-created_at")

class MarkPostViewedView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            post_view, created = PostView.objects.get_or_create(user=request.user, post=post)
            
            if created:
                return Response({'detail': 'Post marked as viewed.'}, status=status.HTTP_201_CREATED)
            else:
                return Response({'detail': 'Post was already marked as viewed.'}, status=status.HTTP_200_OK)
            
        except Post.DoesNotExist:
            return Response({'detail': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)
        
class BulkMarkPostViewedView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        post_ids = request.data.get('post_ids', [])
        
        if not post_ids or not isinstance(post_ids, list):
            return Response({'detail': 'post_ids must be a non-empty list.'}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_posts = Post.objects.filter(id__in=post_ids)
        
        post_views_to_create = []
        for post_id in valid_posts:
            post_view, created = PostView.objects.get_or_create(user=request.user, post_id=post_id)
            if created:
                post_views_to_create.append(post_view)
        
        return Response({
            "message": f"Marked {len(post_views_to_create)} posts as viewed.",
            "total_requests": len(post_ids),
            "valid_requests": len(valid_posts),
            "successful_requests": len(post_views_to_create)
        }, status.HTTP_200_OK)

# Create Comment

class CommentPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page-size'
    max_page_size = 50
    page_query_param = 'page'

class CreateNewCommentView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer
    
    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs["post_id"])
        parent_id = self.request.data.get("parent")
        
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id, post=post)
        serializer.save(author=self.request.user, post=post, parent=parent)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response_serializer = CommentResponseSerializer(serializer.instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        
class CommentPostView(ListAPIView):
    serializer_class = CommentListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CommentPagination
    
    def get_queryset(self):
        user = self.request.user
        
        # This is how you get the post_id from the URL!
        # If URL is /posts/123/comments/, then post_id = 123
        post_id = self.kwargs['post_id']
        queryset = Comment.objects.filter(
            post_id=post_id, # Only comments from this specific post
            moderation_status=ModerationStatus.OK,
            parent__isnull=True # Only top-level comments (no parent)
        ).select_related(
            'author' # Optimise: get author info in same query
        ).prefetch_related(
            'children__author' # Optimise: get all replies and their authors
        )
    
        queryset = self._apply_ordering(queryset)
        return queryset
    
    def _apply_ordering(self, queryset):
        order_by = self.request.query_params.get('order_by', 'likes')
        
        if order_by == 'recent':
            return queryset.order_by('-created_at')
        elif order_by == 'oldest':
            return queryset.order_by('created_at')
        elif order_by == 'likes_asc':
            return queryset.order_by('no_of_likes', 'created_at')
        else:
            return queryset.order_by('-no_of_likes', '-created_at')
        
class LikePostView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        content_type = ContentType.objects.get_for_model(Post)

        post_like, created = Like.objects.get_or_create(user=request.user, content_type=content_type, object_id=post_id)
        
        if created:
            return Response({'detail': 'Post liked.', 'liked': True}, status=status.HTTP_201_CREATED)
        else:
            post_like.delete()
            return Response({'detail': 'Post unliked.', 'liked': False}, status=status.HTTP_200_OK)

class LikeCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)
        content_type = ContentType.objects.get_for_model(Comment)

        comment_like, created = Like.objects.get_or_create(user=request.user, content_type=content_type, object_id=comment_id)
        
        if created:
            return Response({'detail': 'Comment liked.', 'liked': True}, status=status.HTTP_201_CREATED)
        else:
            comment_like.delete()
            return Response({'detail': 'Comment unliked.', 'liked': False}, status=status.HTTP_200_OK)
        
class NotificationPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page-size"
    max_page_size = 100
    page_query_param = "page"


class NotificationsListView(ListAPIView):
    serializer_class = NotificationListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination

    def get_queryset(self):
        qs = (
            Notification.objects.filter(user=self.request.user)
            .select_related("triggered_by", "content_type")
            .prefetch_related(
                GenericPrefetch(
                    "content_object",
                    [
                        Post.objects.only("id"),
                        Comment.objects.select_related("post").only(
                            "id", "post_id", "post__id"
                        ),
                        # FollowRequest.objects.only("id"),
                    ],
                )
            )
            .order_by("-created_at")
        )
        unread_only = self.request.query_params.get("unread_only", "").lower()
        if unread_only in ("1", "true", "yes"):
            qs = qs.filter(is_read=False)
        return qs


# TODO search for posts with potentially various filters
# TODO search by text, author, hashtags