from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CreateNewPostView, ExplorePostsView, MarkPostViewedView, BulkMarkPostViewedView, CreateNewCommentView, GetPostView, CommentPostView, LikeCommentView, LikePostView, ReportPostView, UserPostView, GetCommentView, FollowingPostsView, HashtagPostsView, NotificationsListView, NotificationMarkReadView, UserPostsListView, UserCommentView

urlpatterns = [
    path('create/post/', CreateNewPostView.as_view(), name='create-post'),
    path('post/<int:post_id>/', GetPostView.as_view(), name='get-post'),
    path('explore/', ExplorePostsView.as_view(), name='explore-posts'),
    path('following/', FollowingPostsView.as_view(), name='following-posts'),
    path('hashtag/', HashtagPostsView.as_view(), name='hashtag-posts'),
    path('posts/<int:post_id>/mark-viewed/', MarkPostViewedView.as_view(), name='mark_post_viewed'),
    path('posts/bulk-mark-viewed/', BulkMarkPostViewedView.as_view(), name='bulk_mark_posts_viewed'),
    path('post/<int:post_id>/create/comment/', CreateNewCommentView.as_view(), name='create-comment'),
    path('posts/<int:post_id>/comments/', CommentPostView.as_view(), name='post-comment'),
    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like_post'), 
    path('posts/<int:post_id>/report/', ReportPostView.as_view(), name='report-post'),
    path('comment/<int:comment_id>/like/', LikeCommentView.as_view(), name='like-comment'),
    path('my-post/<int:post_id>/', UserPostView.as_view(), name='user-post'),
    path('comment/<int:comment_id>/', GetCommentView.as_view(), name='get-comment'),
    path('my-comment/<int:comment_id>/', UserCommentView.as_view(), name='user-comment'),
    path('notifications/', NotificationsListView.as_view(), name='notifications-list'),
    path('notifications/<int:notification_id>/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path("posts/user/<str:username>/", UserPostsListView.as_view(), name="user-posts"),
]
