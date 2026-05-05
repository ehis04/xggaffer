from django.contrib import admin
from .models import (
    Club,
    ClubMembership,
    ClubPlayer,
    ClubExternalIdentity,
    ClubJoinRequest,
    ClubInvitation,
    ClubEvent,
    Fixture,
    ClubResource,
    ClubResourceView,
    ClubImportJob,
)


class ClubMembershipInline(admin.TabularInline):
    model = ClubMembership
    extra = 1
    fields = ['user', 'role', 'is_active', 'invited_by']
    raw_id_fields = ['user', 'invited_by']


class ClubPlayerInline(admin.TabularInline):
    model = ClubPlayer
    extra = 0
    fields = ['first_name', 'last_name', 'squad_number', 'primary_position', 'is_active']
    show_change_link = True


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'creator',
        'visibility',
        'club_type',
        'directory_visibility',
        'join_policy',
        'verification_status',
        'city',
        'country',
        'division',
        'member_count',
        'player_count',
        'created_at',
    ]
    list_filter = [
        'visibility',
        'club_type',
        'fictional_basis',
        'directory_visibility',
        'join_policy',
        'verification_status',
        'country',
        'created_at',
    ]
    search_fields = [
        'name',
        'city',
        'creator__email',
        'source_real_club_name',
        'join_code',
    ]
    raw_id_fields = ['creator']
    readonly_fields = ['member_count', 'player_count', 'created_at', 'updated_at']
    ordering = ['name']
    inlines = [ClubMembershipInline, ClubPlayerInline]

    fieldsets = [
        (None, {
            'fields': ['name', 'description', 'badge']
        }),
        ('Ownership and Legacy Visibility', {
            'fields': ['creator', 'visibility']
        }),
        ('Taxonomy', {
            'fields': ['club_type', 'fictional_basis', 'source_real_club_name']
        }),
        ('Discovery and Join', {
            'fields': ['directory_visibility', 'join_policy', 'join_code']
        }),
        ('Verification', {
            'fields': [
                'verification_status',
                'verification_contact_name',
                'verification_contact_role',
                'verification_contact_email',
                'verification_evidence_text',
                'verification_evidence_url',
            ],
            'classes': ['collapse']
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


@admin.register(ClubJoinRequest)
class ClubJoinRequestAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'club',
        'requested_role',
        'status',
        'reviewed_by',
        'reviewed_at',
        'created_at',
    ]
    list_filter = ['status', 'requested_role', 'club', 'created_at']
    search_fields = ['user__email', 'club__name', 'message', 'review_note']
    raw_id_fields = ['user', 'club', 'reviewed_by', 'selected_club_player']
    readonly_fields = ['created_at', 'updated_at', 'reviewed_at']
    ordering = ['-created_at']


@admin.register(ClubInvitation)
class ClubInvitationAdmin(admin.ModelAdmin):
    list_display = [
        'invited_user',
        'club',
        'invited_role',
        'status',
        'invited_by',
        'responded_at',
        'created_at',
    ]
    list_filter = ['status', 'invited_role', 'club', 'created_at']
    search_fields = ['invited_user__email', 'club__name', 'note', 'response_note']
    raw_id_fields = ['invited_user', 'club', 'invited_by']
    readonly_fields = ['created_at', 'updated_at', 'responded_at']
    ordering = ['-created_at']


@admin.register(ClubPlayer)
class ClubPlayerAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'club',
        'squad_number',
        'primary_position',
        'is_active',
        'is_claimed',
    ]
    list_filter = ['primary_position', 'is_active', 'club']
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
            'fields': ['squad_number', 'primary_position', 'secondary_position', 'preferred_foot']
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


@admin.register(ClubExternalIdentity)
class ClubExternalIdentityAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'provider',
        'external_id',
        'club',
        'provider_display_name',
        'is_primary',
        'last_synced_at',
    ]
    list_filter = ['provider', 'is_primary']
    search_fields = ['external_id', 'provider_display_name', 'club__name']
    raw_id_fields = ['club']
    ordering = ['provider', 'external_id', 'id']

@admin.register(ClubEvent)
class ClubEventAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'club',
        'event_type',
        'source_type',
        'start_datetime',
        'is_all_day',
        'is_mandatory',
        'created_by',
    ]
    list_filter = [
        'event_type',
        'source_type',
        'is_all_day',
        'is_mandatory',
        'club',
    ]
    search_fields = ['title', 'description', 'location', 'club__name']
    raw_id_fields = ['club', 'created_by']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['start_datetime', 'id']


@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display = [
        'club',
        'opponent_name',
        'venue',
        'competition',
        'match_datetime',
        'fixture_status',
        'source_type',
        'created_by',
    ]
    list_filter = [
        'venue',
        'fixture_status',
        'source_type',
        'club',
    ]
    search_fields = [
        'club__name',
        'opponent_name',
        'competition',
        'location',
        'external_fixture_id',
    ]
    raw_id_fields = ['club', 'created_by']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['match_datetime', 'id']

@admin.register(ClubResource)
class ClubResourceAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'club',
        'file_kind',
        'storage_backend',
        'engagement_visibility',
        'is_archived',
        'uploaded_by',
        'created_at',
    ]
    list_filter = [
        'file_kind',
        'storage_backend',
        'engagement_visibility',
        'is_archived',
        'club',
        'created_at',
    ]
    search_fields = [
        'title',
        'description',
        'original_filename',
        'mime_type',
        'storage_key',
        'club__name',
        'uploaded_by__email',
    ]
    raw_id_fields = ['club', 'uploaded_by']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at', '-id']


@admin.register(ClubResourceView)
class ClubResourceViewAdmin(admin.ModelAdmin):
    list_display = [
        'resource',
        'user',
        'opened',
        'completed',
        'total_active_seconds',
        'highest_page_reached',
        'first_opened_at',
        'last_opened_at',
    ]
    list_filter = [
        'opened',
        'completed',
        'resource__club',
        'resource__engagement_visibility',
    ]
    search_fields = [
        'resource__title',
        'resource__club__name',
        'user__email',
    ]
    raw_id_fields = ['resource', 'user']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['resource_id', '-last_opened_at', '-updated_at']

@admin.register(ClubImportJob)
class ClubImportJobAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'club',
        'import_type',
        'status',
        'source_resource',
        'uploaded_by',
        'row_count',
        'valid_row_count',
        'imported_row_count',
        'created_at',
    ]
    list_filter = [
        'import_type',
        'status',
        'club',
        'created_at',
    ]
    search_fields = [
        'club__name',
        'source_resource__title',
        'source_resource__original_filename',
        'uploaded_by__email',
    ]
    raw_id_fields = ['club', 'uploaded_by', 'source_resource']
    readonly_fields = [
        'created_at',
        'updated_at',
        'started_at',
        'completed_at',
    ]
    ordering = ['-created_at', '-id']