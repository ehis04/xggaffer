"""
Django admin configuration for article recommendation models

Registers article sites, authors, topics, articles, user profiles, ratings, feedback, recommendations, and reading history for admin management
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Site, Author, Topic, Article, UserProfile,
    ArticleRating, UserFeedback, UserRecommendation, ReadingHistory,
)


# Admin configuration for article source sites
@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'reputation_score', 'total_likes', 'total_dislikes', 'sentiment_display']
    list_filter = ['name', 'is_active']
    search_fields = ['name']
    readonly_fields = ['total_likes', 'total_dislikes', 'created_at', 'updated_at']

    # Display the site sentiment score with colour-coded formatting
    def sentiment_display(self, obj):
        score = obj.user_sentiment_score
        color = 'green' if score > 0.6 else 'orange' if score > 0.4 else 'red'
        return format_html('<span style="color: {};">{:.1f%}</span>', color, score)

    sentiment_display.short_description = 'User Sentiment'


# Admin configuration for article authors
@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'expertise_score', 'credibility_score']
    list_filter = ['sites', 'is_verified']
    search_fields = ['name', 'email']
    filter_horizontal = ['sites']
    readonly_fields = ['total_likes', 'total_dislikes', 'created_at', 'updated_at']

    # Display the author sentiment score with colour-coded formatting
    def sentiment_display(self, obj):
        score = obj.user_sentiment_score
        color = 'green' if score > 0.6 else 'orange' if score > 0.4 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f%}</span>',
            color, score
        )

    sentiment_display.short_description = 'User Sentiment'


# Admin configuration for article topics
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


# Admin configuration for article records
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'site', 'publication_date', 'quality_score']
    list_filter = ['site', 'publication_date', 'topics', 'is_featured', 'is_active']
    search_fields = ['title', 'summary']
    filter_horizontal = ['topics']
    readonly_fields = [
        'slug',
        'scraped_date',
        'view_count',
        'total_ratings',
        'average_rating',
        'total_likes',
        'total_dislikes',
        'created_at',
        'updated_at',
    ]
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'publication_date'

    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'slug', 'url', 'summary', 'image_url')
        }),
        ('Relationships', {
            'fields': ('site', 'authors', 'topics')
        }),
        ('Dates', {
            'fields': ('publication_date', 'scraped_date')
        }),
        ('Content Metrics', {
            'fields': ('word_count', 'read_time_minutes')
        }),
        ('Quality Scores', {
            'fields': ('quality_score', 'readability_score', 'factual_score', 'engagement_score')
        }),
        ('External Metrics', {
            'fields': ('external_shares', 'external_comments', 'external_rating')
        }),
        ('User Engagement', {
            'fields': ('view_count', 'total_ratings', 'average_rating', 'total_likes', 'total_dislikes')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
    )


# Admin configuration for article user preference profiles
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['articles_read', 'last_active', 'user']
    filter_horizontal = ['preferred_topics', 'preferred_authors', 'preferred_sites']
    readonly_fields = ['articles_read', 'created_at', 'updated_at', 'last_active']
    search_fields = ['user']


# Admin configuration for user article ratings
@admin.register(ArticleRating)
class ArticleRatingAdmin(admin.ModelAdmin):
    list_display = ['article', 'user', 'rating', 'created_at']
    list_filter = ['created_at', 'rating']
    search_fields = ['user__username', 'article__title']
    readonly_fields = ['created_at', 'updated_at']

    # Return a shortened article title for admin display
    def article_title(self, obj):
        return obj.article.title[:50]

    article_title.short_description = 'Article'


# Admin configuration for user feedback records
@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'author', 'feedback_type', 'target_type']
    list_filter = ['user', 'feedback_type', 'target_type']
    search_fields = ['user__username', 'author']

    # Return the active feedback target name for admin display
    def target_name(self, obj):
        target = obj.article or obj.author or obj.site
        return str(target)[:50]

    target_name.short_description = 'Target'


# Admin configuration for generated article recommendations
@admin.register(UserRecommendation)
class UserRecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'article', 'score', 'position', 'is_viewed', 'is_clicked']
    list_filter = ['is_clicked']
    search_fields = ['user__username', 'article__title']

    # Return a shortened article title for admin display
    def article_title(self, obj):
        return obj.article.title[:50]

    article_title.short_description = 'Article'


# Admin configuration for article reading history
@admin.register(ReadingHistory)
class ReadingHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'article', 'time_spent_seconds', 'completed']
    list_filter = ['completed', 'read_at']
    search_fields = ['user__username', 'article__title']
    readonly_fields = ['read_at']

    # Return a shortened article title for admin display
    def article_title(self, obj):
        return obj.article.title[:50]

    article_title.short_description = 'Article'