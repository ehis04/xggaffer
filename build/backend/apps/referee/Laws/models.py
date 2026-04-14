from django.db import models


class Law(models.Model):
    law_number  = models.PositiveSmallIntegerField(unique=True)
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order       = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['law_number']

    def __str__(self):
        return f"Law {self.law_number}: {self.title}"


class CourseSection(models.Model):
    law   = models.ForeignKey(Law, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.law} — {self.title}"


class ItemType(models.TextChoices):
    CLAUSE   = 'clause',   'Clause'
    SCENARIO = 'scenario', 'Scenario'
    DRILL    = 'drill',    'Drill'
    QUIZ     = 'quiz',     'Quiz'


class CourseItem(models.Model):
    section   = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=10, choices=ItemType.choices)
    title     = models.CharField(max_length=300)
    order     = models.PositiveSmallIntegerField(default=0)
    mins      = models.PositiveSmallIntegerField(default=3)

    clause_number = models.PositiveSmallIntegerField(null=True, blank=True)
    clause_text   = models.TextField(blank=True)

    scenario_situation   = models.TextField(blank=True)
    scenario_options     = models.JSONField(default=list, blank=True)
    scenario_correct_id  = models.CharField(max_length=10, blank=True)
    scenario_explanation = models.TextField(blank=True)

    drill_description = models.TextField(blank=True)
    drill_items       = models.JSONField(default=list, blank=True)

    quiz_id             = models.CharField(max_length=50, blank=True)
    quiz_question_count = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"[{self.item_type}] {self.title}"