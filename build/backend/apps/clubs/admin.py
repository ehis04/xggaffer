from django.contrib import admin
from .models import Club, ClubMembership, PlayerProfile


class ClubMembershipInline(admin.TabularInline):
    model = ClubMembership
    extra = 1
    fields = ['user', 'role', 'is_active', 'invited_by']
    raw_id_fields = ['user', 'invited_by']


class PlayerProfileInline(admin.TabularInline):
    model = PlayerProfile
    extra = 0
    fields = ['first_name', 'last_name', 'squad_number', 'position', 'is_active']
    show_change_link = True


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'creator',
        'visibility',
        'city',
        'country',
        'division',
        'member_count',
        'player_count',
        'created_at',
    ]
    list_filter = ['visibility', 'country', 'created_at']
    search_fields = ['name', 'city', 'creator__email']
    raw_id_fields = ['creator']
    readonly_fields = ['member_count', 'player_count', 'created_at', 'updated_at']
    ordering = ['name']
    inlines = [ClubMembershipInline, PlayerProfileInline]

    fieldsets = [
        (None, {
            'fields': ['name', 'description', 'badge']
        }),
        ('Ownership', {
            'fields': ['creator', 'visibility']
        }),
        ('Location', {
            'fields': ['city', 'country', 'stadium'],
            'classes': ['collapse']
        }),
        ('Competition', {
            'fields': ['division', 'achievements'],
            'classes': ['collapse']
        }),
        ('Stats', {
            'fields': ['member_count', 'player_count'],
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(ClubMembership)
class ClubMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'club', 'role', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active', 'club']
    search_fields = ['user__email', 'club__name']
    raw_id_fields = ['user', 'club', 'invited_by']
    readonly_fields = ['joined_at', 'updated_at']
    ordering = ['club', 'role']


@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'club',
        'squad_number',
        'position',
        'is_active',
        'is_claimed',
    ]
    list_filter = ['position', 'is_active', 'club']
    search_fields = ['first_name', 'last_name', 'club__name', 'user__email']
    raw_id_fields = ['club', 'user', 'created_by']
    readonly_fields = ['full_name', 'is_claimed', 'claimed_at', 'created_at', 'updated_at']
    ordering = ['club', 'squad_number', 'last_name']

    fieldsets = [
        (None, {
            'fields': ['club', 'user', 'is_active']
        }),
        ('Identity', {
            'fields': ['first_name', 'last_name', 'display_name', 'full_name', 'photo']
        }),
        ('Football', {
            'fields': ['squad_number', 'position', 'secondary_position', 'preferred_foot']
        }),
        ('Physical', {
            'fields': ['date_of_birth', 'height_cm'],
            'classes': ['collapse']
        }),
        ('Claim Status', {
            'fields': ['is_claimed', 'claim_token', 'claimed_at'],
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ['created_by', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]