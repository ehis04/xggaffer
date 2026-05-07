"""
Admin configuration for teamsheet models

Adds inline player editing and searchable admin views for teamsheets and teamsheet player assignments
"""

from django.contrib import admin

from .models import *


# Inline admin rows for players assigned to a teamsheet
class TeamsheetPlayerInline(admin.TabularInline):
    model = TeamsheetPlayer
    extra = 0
    fields = [
        'slot_number',
        'club_player',
        'custom_name',
        'custom_number',
        'position_label',
        'position_x',
        'position_y',
        'is_substitute',
    ]
    raw_id_fields = ['club_player']
    ordering = ['is_substitute', 'slot_number']


# Admin view for teamsheets
@admin.register(Teamsheet)
class TeamsheetAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'club',
        'formation',
        'opponent',
        'match_date',
        'is_template',
        'starter_count',
        'created_by',
        'updated_at',
    ]
    list_filter = ['formation', 'is_template', 'club', 'created_at']
    search_fields = ['title', 'opponent', 'club__name', 'created_by__username']
    raw_id_fields = ['club', 'created_by']
    readonly_fields = ['created_at', 'updated_at', 'starter_count', 'substitute_count', 'is_complete']
    date_hierarchy = 'created_at'
    ordering = ['-updated_at']
    inlines = [TeamsheetPlayerInline]
    
    fieldsets = [
        (None, {
            'fields': ['title', 'club', 'created_by']
        }),
        ('Formation', {
            'fields': ['formation', 'is_template']
        }),
        ('Match Details', {
            'fields': ['match_date', 'opponent', 'notes'],
            'classes': ['collapse']
        }),
        ('Status', {
            'fields': ['starter_count', 'substitute_count', 'is_complete'],
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    # Return the number of starters on a teamsheet
    def starter_count(self, obj):
        return obj.starter_count
    starter_count.short_description = 'Starters'

    # Return the number of substitutes on a teamsheet
    def substitute_count(self, obj):
        return obj.substitute_count
    substitute_count.short_description = 'Subs'


# Admin view for individual teamsheet player rows
@admin.register(TeamsheetPlayer)
class TeamsheetPlayerAdmin(admin.ModelAdmin):
    list_display = [
        'display_name',
        'teamsheet',
        'position_label',
        'slot_number',
        'is_substitute',
        'is_linked',
    ]
    list_filter = ['position_label', 'is_substitute', 'teamsheet__club']
    search_fields = [
        'custom_name',
        'club_player__player__first_name',
        'club_player__player__last_name',
        'teamsheet__title',
    ]
    raw_id_fields = ['teamsheet', 'club_player']
    readonly_fields = ['display_name', 'display_number', 'is_linked', 'created_at', 'updated_at']
    ordering = ['teamsheet', 'is_substitute', 'slot_number']
    
    fieldsets = [
        (None, {
            'fields': ['teamsheet', 'slot_number', 'is_substitute']
        }),
        ('Player', {
            'fields': ['club_player', 'custom_name', 'custom_number'],
            'description': 'Link to a club player OR enter custom details'
        }),
        ('Position', {
            'fields': ['position_label', 'position_x', 'position_y']
        }),
        ('Display Values', {
            'fields': ['display_name', 'display_number', 'is_linked'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    # Return the resolved player display name
    def display_name(self, obj):
        return obj.display_name
    display_name.short_description = 'Display Name'

    # Return whether the row is linked to a club player
    def is_linked(self, obj):
        return obj.is_linked
    is_linked.boolean = True
    is_linked.short_description = 'Linked'