from django.db import models
from django.contrib.postgres.fields import JSONField

class LawEdition(models.Model):
    year = models.CharField(max_length=7, unique=True)
    publication_date = models.DateField()
    is_current = models.BooleanField(default=False)
    pdf_url = models.URLField()
    pdf_file = models.FileField(upload_to='laws_pdfs/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-publication_date']

class Law(models.Model):
    edition = models.ForeignKey(LawEdition, related_name='laws', on_delete=models.CASCADE)
    number = models.IntegerField()
    title = models.CharField(max_length=255)
    full_content = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('edition', 'number')
        ordering = ['number']

class LawClause(models.Model):
    law = models.ForeignKey(Law, related_name='clauses', on_delete=models.CASCADE)
    clause_id = models.CharField(max_length=20)
    heading = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    examples = models.JSONField(default=list)
    notes = models.JSONField(default=list)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

class LawChange(models.Model):
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

class ParsingJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('review', 'Needs Review'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    edition = models.ForeignKey(LawEdition, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    parsed_data = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)