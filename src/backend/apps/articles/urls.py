"""
URL routes for article recommendation APIs

Maps article feeds, favourites, detail pages, ratings, feedback, reading history, lookup lists, and profile preferences to their API views
"""

from django.urls import path
from .views import (
    ArticleFeedView,
    FavoriteArticleFeedView,
    ArticleDetailView,
    ArticleRateView,
    ArticleFeedbackView,
    ArticleFavoriteToggleView,
    MarkReadView,
    TopicListView,
    SiteListView,
    AuthorListView,
    UserArticleProfileView,
)


# Article API route definitions
urlpatterns = [
    path('feed/', ArticleFeedView.as_view(), name='article-feed'),
    path('favourites/feed/', FavoriteArticleFeedView.as_view(), name='article-favourites-feed'),
    path('<int:article_id>/', ArticleDetailView.as_view(), name='article-detail'),
    path('<int:article_id>/favorite/', ArticleFavoriteToggleView.as_view(), name='article-favorite-toggle'),
    path('<int:article_id>/rate/', ArticleRateView.as_view(), name='article-rate'),
    path('<int:article_id>/read/', MarkReadView.as_view(), name='article-mark-read'),
    path('feedback/', ArticleFeedbackView.as_view(), name='article-feedback'),
    path('topics/', TopicListView.as_view(), name='article-topics'),
    path('sites/', SiteListView.as_view(), name='article-sites'),
    path('authors/', AuthorListView.as_view(), name='article-authors'),
    path('profile/', UserArticleProfileView.as_view(), name='article-profile'),
]