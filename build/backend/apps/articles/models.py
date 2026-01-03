"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta

#User = get_user_model()

class Site(models.Model):
    name = models.CharField(max_length=100, blank=False)
    domain = models.CharField(max_length=100, blank=False, unique=True) #url field?
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)

    reputation_score = models.FloatField(
        default=50.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)], #?
        help_text="Aggregated quality score (0-100)"
    )
    alexa_rank = models.IntegerField(null=True, blank=True)
    trust_score = models.FloatField(default=50.0)

    total_likes = models.IntegerField(default=0)
    total_dislikes = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering =['-reputation_score']

    def __str__(self):
        return self.name    #whats this and the meta bit for?

    @property
    def user_sentiment_score(self):
        total = self.total_likes + self.total_dislikes
        if total == 0:
            return 0.5
        return self.total_likes / total


class Topic(models.Model):
    name = models.CharField(max_length=100, blank=False, unique=True)
    slug = models.SlugField(max_length=100, blank=False, unique=True) #whats slugfield for?
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='subtopics') 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Article(models.Model):
    title = models.CharField(max_length=255, blank=False)
    slug = models.SlugField(max_length=500, unique=True)
    url = models.URLField(unique=True)

    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    image_url = models.URLField(blank=True)

    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    authors = models.ManyToManyField('Author', related_name='articles', blank=True) 
    topics = models.ManyToManyField(Topic, related_name='articles')

    publication_date = models.DateTimeField()
    scraped_date = models.DateTimeField(auto_now_add=True)
    word_count = models.IntegerField(default=0)
    read_time_minutes = models.IntegerField(default=5)

    quality_score = models.FloatField(default=50.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)], help_text="Composite quality score (0-100)")
    readability_score = models.FloatField(default=50.0)
    engagement_score = models.FloatField(default=50.0)

    external_shares = models.IntegerField(default=0)
    external_comments = models.IntegerField(default=0)
    external_rating = models.FloatField(null=True, blank=True)

    view_count = models.IntegerField(default=0)
    total_ratings = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    total_likes = models.IntegerField(default=0)
    total_dislikes = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-publication_date']
        indexes = [
            models.Index(fields=['-publication_date']),
            models.Index(fields=['-quality_score']),
            models.Index(fields=['site', '-publication_date'])
        ]

    def __str__(self):
        return self.title

    @property
    def is_recent(self):
        return self.publication_date >= timezone.now() - timedelta(days=7)

    @property
    def user_sentiment_score(self):
        total = self.total_likes + self.total_dislikes
        if total == 0:
            return 0.5
        return self.total_likes / total


class Author(models.Model):
    name = models.CharField(max_length=100, blank=False)
    email = models.EmailField(unique=True, blank=True, null=True)
    bio = models.TextField(blank=True)
    profile_url = models.URLField(blank=True)
    avatar_url = models.URLField(blank=True)

    sites = models.ManyToManyField(Site, related_name='authors', blank=True)
    
    expertise_score = models.FloatField(default=50.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    credibility_score = models.FloatField(default=50.0)

    total_likes = models.IntegerField(default=0)
    total_dislikes = models.IntegerField(default=0)

    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def user_sentiment_score(self):
        total = self.total_likes + self.total_dislikes
        if total == 0:
            return 0.5
        return self.total_likes / total

    #user_feedback_score = models.FloatField(default=0.0)
        
class ArticleRating(models.Model):
    RATING_CHOICES = [
        (1, 'Poor'),
        (2, 'Fair'),
        (3, 'Good'),
        (4, 'Very Good'),
        (5, 'Excellent'),
    ]

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='article_ratings')
    rating = models.IntegerField(choices=RATING_CHOICES)
    review = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('article', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.article.title[:50]} ({self.rating}⭐)"

class UserFeedback(models.Model):
    FEEDBACK_TYPES = [
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    ]

    TARGET_TYPES = [
        ('article', 'Article'),
        ('author', 'Author'),
        ('site', 'Site'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    feedback_type = models.CharField(max_length=10, choices=FEEDBACK_TYPES)
    target_type = models.CharField(max_length=20, choices=TARGET_TYPES)

    article = models.ForeignKey(Article, null=True, blank=True, on_delete=models.CASCADE, related_name='feedbacks')
    author = models.ForeignKey(Author, null=True, blank=True, on_delete=models.CASCADE, related_name='feedbacks')
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.CASCADE, related_name='feedbacks')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'target_type']),
            models.Index(fields=['article'])
        ]

    def __str__(self):
        target = self.article or self.author or self.site
        return f"{self.user.email} - {self.feedback_type}s {target}"

class UserRecommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='recommendeds')

    score = models.FloatField(help_text="Recommendation confidence score")
    reason = models.TextField(max_length=500, blank=True, help_text="Why was this recommended")
    position = models.IntegerField(help_text="Position in the recommendation list")

    is_viewed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(null=True, blank=True)
    is_clicked = models.BooleanField(default=False)
    clivked_at = models.DateTimeField(null=True, blank=True)

    batch_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'article', 'batch_date')
        ordering = ['position']
        indexes = [
            models.Index(fields=['user', 'batch_date']),
            models.Index(fields=['user', '-score'])
        ]

    def __str__(self):
        return f"{self.user.email} - {self.article[:50]} ({self.score:.2f})"

class ReadingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_histories')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='reading_histories')

    time_spent_seconds = models.IntegerField(default=0)
    scroll_depth_percentage = models.FloatField(default=0.0)
    completed = models.BooleanField(default=False)
    
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'article')
        ordering = ['-read_at']
        verbose_name_plural = "Reading Histories"

    def __str__(self):
        return f"{self.user.email} read {self.article.title[:50]}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='article_profile')

    preferred_topics = models.ManyToManyField(Topic, related_name='interested_users', blank=True)
    preferred_authors = models.ManyToManyField(Author, related_name='followers', blank=True)
    preferred_sites = models.ManyToManyField(Site, related_name='followers', blank=True)

    min_read_time = models.IntegerField(default=0, help_text="Minimum read time in minutes")
    max_read_time = models.IntegerField(default=0, help_text="Maximum read time in minutes")
    preferred_quality_threshold = models.FloatField(default=50.0)

    articles_read = models.IntegerField(default=0)
    articles_rated = models.IntegerField(default=0)
    last_active = models.DateTimeField(auto_now=True)

    daily_recommendation_count = models.IntegerField(default=50)
    enable_auto_refresh = models.BooleanField(default=True)
    last_recommendation_refresh = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.email}"
"""