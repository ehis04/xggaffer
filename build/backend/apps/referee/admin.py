from django.contrib import admin
from apps.referee.Laws.models import Law, CourseSection, CourseItem
from apps.referee.profile.models import RefereeProfile
from apps.referee.progressTracking.models import (
    UserCourseProgress,
    UserItemProgress,
    StudyStreak,
    PerformanceScore,
)

class CourseSectionInline(admin.TabularInline):
    model    = CourseSection
    extra    = 1
    fields   = ('title', 'order')
    ordering = ('order',)


class CourseItemInline(admin.TabularInline):
    model    = CourseItem
    extra    = 1
    fields   = ('item_type', 'title', 'order', 'mins')
    ordering = ('order',)

@admin.register(Law)
class LawAdmin(admin.ModelAdmin):
    list_display  = ('law_number', 'title', 'order')
    list_editable = ('order',)
    ordering      = ('law_number',)
    inlines       = [CourseSectionInline]


@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ('law', 'title', 'order')
    list_filter  = ('law',)
    ordering     = ('law__law_number', 'order')
    inlines      = [CourseItemInline]


@admin.register(CourseItem)
class CourseItemAdmin(admin.ModelAdmin):
    list_display  = ('title', 'item_type', 'section', 'order', 'mins')
    list_filter   = ('item_type', 'section__law')
    search_fields = ('title',)
    ordering      = ('section__law__law_number', 'section__order', 'order')

    readonly_fields = ('scenario_options', 'drill_items')

    fieldsets = (
        (None, {
            'fields': ('section', 'item_type', 'title', 'order', 'mins'),
        }),
        ('Clause', {
            'classes': ('collapse',),
            'fields':  ('clause_number', 'clause_text'),
        }),
        ('Scenario', {
            'classes': ('collapse',),
            'fields':  (
                'scenario_situation',
                'scenario_options',
                'scenario_correct_id',
                'scenario_explanation',
            ),
        }),
        ('Drill', {
            'classes': ('collapse',),
            'fields':  (
                'drill_description',
                'drill_items',
            ),
        }),
        ('Quiz', {
            'classes': ('collapse',),
            'fields':  ('quiz_id', 'quiz_question_count'),
        }),
    )

@admin.register(RefereeProfile)
class RefereeProfileAdmin(admin.ModelAdmin):
    list_display  = ('user_profile', 'years_experience', 'created_at')
    search_fields = ('user_profile__user__username',)
    ordering      = ('user_profile__user__username',)

@admin.register(UserCourseProgress)
class UserCourseProgressAdmin(admin.ModelAdmin):
    list_display    = (
        'user_profile', 'law', 'status',
        'clauses_read', 'total_clauses', 'progress_percentage',
        'last_accessed',
    )
    list_filter     = ('status', 'law')
    search_fields   = ('user_profile__user__username',)
    ordering        = ('user_profile__user__username', 'law__law_number')
    readonly_fields = ('progress_percentage', 'started_at', 'completed_at', 'last_accessed')


@admin.register(UserItemProgress)
class UserItemProgressAdmin(admin.ModelAdmin):
    list_display  = (
        'user_profile', 'item', 'completed', 'completed_at',
        'scenario_correct', 'drill_submitted',
    )
    list_filter   = ('completed', 'item__item_type', 'scenario_correct', 'drill_submitted')
    search_fields = ('user_profile__user__username', 'item__title')
    ordering      = ('-completed_at',)
    readonly_fields = (
        'completed_at',
        'scenario_selected_id', 'scenario_correct',
        'drill_answers', 'drill_submitted',
    )


@admin.register(StudyStreak)
class StudyStreakAdmin(admin.ModelAdmin):
    list_display    = ('user_profile', 'current_streak', 'last_updated')
    search_fields   = ('user_profile__user__username',)
    ordering        = ('-current_streak',)
    readonly_fields = ('studied_dates', 'last_updated')


@admin.register(PerformanceScore)
class PerformanceScoreAdmin(admin.ModelAdmin):
    list_display  = (
        'user_profile', 'overall_score',
        'clause_score', 'scenario_score', 'drill_score', 'quiz_score',
        'updated_at',
    )
    search_fields = ('user_profile__user__username',)
    ordering      = ('-overall_score',)
    readonly_fields = (
        'overall_score',
        'clause_score', 'scenario_score', 'drill_score', 'quiz_score',
        'updated_at',
    )