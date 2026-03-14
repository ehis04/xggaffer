from django.db import models
from django.contrib.postgres.fields import JSONField

class LawEdition(models.Model):
    """Tracks different editions of the Laws of the Game by year"""
    year = models.CharField(max_length=7, unique=True)  # e.g., "2025/26"
    publication_date = models.DateField()
    is_current = models.BooleanField(default=False)
    pdf_url = models.URLField()
    pdf_file = models.FileField(upload_to='laws_pdfs/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-publication_date']
        verbose_name = ("Law Edition")
        verbose_name_plural = ("Law Editions")

    def __str__(self):
        return f"Laws {self.year}"
    
    def save(self, *args, **kwargs):
        # Ensure only one edition is marked as current
        if self.is_current:
            LawEdition.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class Law(models.Model):
    """Represents one of the 17 Laws of the Game"""
    DIFFICULTY_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    edition = models.ForeignKey(LawEdition, related_name='laws', on_delete=models.CASCADE)
    number = models.IntegerField()  # 1-17
    title = models.CharField(max_length=255)
    
    # Enhanced fields for learning platform
    description = models.TextField(blank=True)  # Brief overview
    icon = models.CharField(max_length=50, blank=True)  # Icon identifier for UI
    difficulty_level = models.CharField(
        max_length=20, 
        choices=DIFFICULTY_LEVELS,
        default='intermediate'
    )
    estimated_time_minutes = models.PositiveIntegerField(default=30)
    
    # Original field - stores full extracted content
    full_content = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('edition', 'number')
        ordering = ['number']
        verbose_name = ("Law")
        verbose_name_plural = ("Laws")
        indexes = [
            models.Index(fields=['edition', 'number']),
            models.Index(fields=['difficulty_level']),
        ]

    def __str__(self):
        return f"Law {self.number}: {self.title}"
    
    @property
    def clause_count(self):
        return self.clauses.count()
    
    @property
    def quiz_count(self):
        return self.quizzes.filter(is_active=True).count()

class LawClause(models.Model):
    """
    Subsections within each law (equivalent to LawSection in original design).
    Renamed to match existing codebase.
    """
    law = models.ForeignKey(Law, related_name='clauses', on_delete=models.CASCADE)
    clause_id = models.CharField(max_length=20)  # e.g., "1", "2", "1.1"
    heading = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    
    # Structured data
    examples = models.JSONField(default=list)  # List of examples
    notes = models.JSONField(default=list)  # Additional notes
    bullet_points = models.JSONField(default=list)  # Key points extracted from content
    
    # Visual aids
    diagram_url = models.URLField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = ("Law Clause")
        verbose_name_plural = ("Law Clauses")
        indexes = [
            models.Index(fields=['law', 'order']),
        ]
        unique_together = ['law', 'clause_id']

    def __str__(self):
        return f"Law {self.law.number}.{self.clause_id} - {self.heading}"

class LawChange(models.Model):
    """Tracks changes between editions for historical tracking"""
    CHANGE_TYPES = [
        ('added', 'Added'),
        ('modified', 'Modified'),
        ('removed', 'Removed'),
        ('clarified', 'Clarified'),
    ]
    
    edition = models.ForeignKey(LawEdition, on_delete=models.CASCADE, related_name='changes')
    law_number = models.IntegerField()
    clause_id = models.CharField(max_length=20, blank=True)
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES)
    description = models.TextField()
    old_content = models.TextField(blank=True)
    new_content = models.TextField(blank=True)

    class Meta:
        ordering = ['law_number', 'clause_id']
        verbose_name = ("Law Change")
        verbose_name_plural = ("Law Changes")

    def __str__(self):
        return f"Law {self.law_number} - {self.get_change_type_display()}"

class ParsingJob(models.Model):
    """Tracks PDF parsing jobs for admin monitoring"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('review', 'Needs Review'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    edition = models.ForeignKey(LawEdition, on_delete=models.CASCADE, related_name='parsing_jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    parsed_data = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = ("Parsing Job")
        verbose_name_plural = ("Parsing Jobs")
        ordering = ['-created_at']

    def __str__(self):
        return f"Parsing {self.edition.year} - {self.status}"
    

    
class KeyConcept(models.Model):
    """Important terms and definitions within laws"""
    law = models.ForeignKey(Law, on_delete=models.CASCADE, related_name='key_concepts')
    clause = models.ForeignKey(
        LawClause, 
        on_delete=models.CASCADE, 
        related_name='key_concepts',
        null=True,
        blank=True
    )
    
    term = models.CharField(max_length=200)  # e.g., "Deliberate play"
    definition = models.TextField()
    example = models.TextField(blank=True)  # Real-world example
    
    # For glossary and quick reference
    is_critical = models.BooleanField(default=False)  # Must-know concept
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['term']
        verbose_name = ("Key Concept")
        verbose_name_plural = ("Key Concepts")
        indexes = [
            models.Index(fields=['law']),
            models.Index(fields=['is_critical']),
        ]
    
    def __str__(self):
        return f"{self.term} - Law {self.law.number}"