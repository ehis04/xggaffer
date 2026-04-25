from django.urls import path
from .views import (
    ArticleFeedView,
    ArticleDetailView,
    ArticleRateView,
    ArticleFeedbackView,
    MarkReadView,
    TopicListView,
    SiteListView,
    AuthorListView,
    UserArticleProfileView,
)

urlpatterns = [
    path('feed/', ArticleFeedView.as_view(), name='article-feed'),
    path('<int:article_id>/', ArticleDetailView.as_view(), name='article-detail'),
    path('<int:article_id>/rate/', ArticleRateView.as_view(), name='article-rate'),
    path('<int:article_id>/read/', MarkReadView.as_view(), name='article-mark-read'),
    path('feedback/', ArticleFeedbackView.as_view(), name='article-feedback'),
    path('topics/', TopicListView.as_view(), name='article-topics'),
    path('sites/', SiteListView.as_view(), name='article-sites'),
    path('authors/', AuthorListView.as_view(), name='article-authors'),
    path('profile/', UserArticleProfileView.as_view(), name='article-profile'),
]
