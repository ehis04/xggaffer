"""
Admin configuration for tactics board models

Adds searchable and filterable admin views for tactics boards, animation frames, and frame items
"""

from django.contrib import admin

from apps.tactics.models import TacticsBoard, TacticsBoardFrame, TacticsBoardItem


# Inline admin rows for frames inside a tactics board
class TacticsBoardFrameInline(admin.TabularInline):
    model = TacticsBoardFrame
    extra = 0
    fields = ('frame_index', 'label', 'duration_ms', 'notes')
    ordering = ('frame_index',)
    show_change_link = True


# Admin view for tactics boards
@admin.register(TacticsBoard)
class TacticsBoardAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'club',
        'board_type',
        'pitch_orientation',
        'created_by',
        'updated_at',
    )
    list_filter = (
        'board_type',
        'pitch_orientation',
        'is_template',
        'club',
    )
    search_fields = (
        'title',
        'description',
        'club__name',
        'created_by__email',
    )
    autocomplete_fields = (
        'club',
        'created_by',
        'linked_teamsheet',
    )
    inlines = [TacticsBoardFrameInline]
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)


# Admin view for tactics board frames
@admin.register(TacticsBoardFrame)
class TacticsBoardFrameAdmin(admin.ModelAdmin):
    list_display = (
        'board',
        'frame_index',
        'label',
        'duration_ms',
    )
    list_filter = ('board__club',)
    search_fields = (
        'board__title',
        'label',
        'notes',
    )
    autocomplete_fields = ('board',)
    ordering = ('board', 'frame_index')


# Admin view for items placed on tactics board frames
@admin.register(TacticsBoardItem)
class TacticsBoardItemAdmin(admin.ModelAdmin):
    list_display = (
        'frame',
        'item_type',
        'team_side',
        'stable_id',
        'linked_player',
        'x',
        'y',
    )
    list_filter = (
        'item_type',
        'team_side',
        'frame__board__club',
    )
    search_fields = (
        'label',
        'position_label',
        'linked_player__display_name',
        'linked_player__first_name',
        'linked_player__last_name',
    )
    autocomplete_fields = (
        'frame',
        'linked_player',
    )
    ordering = ('frame', 'z_index', 'id')