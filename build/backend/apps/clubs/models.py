import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from common.constants import *
from apps.players.models import ExternalProvider, Player

class Club(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Private'
        PUBLIC = 'public', 'Public'

    class ClubType(models.TextChoices):
        SYSTEM_PROFESSIONAL = 'system_professional', 'System Professional'
        USER_REAL_NON_PRO = 'user_real_non_pro', 'User Real Non-Pro'
        USER_FICTIONAL = 'user_fictional', 'User Fictional'

    class FictionalBasis(models.TextChoices):
        ORIGINAL = 'original', 'Original'
        REAL_CLUB_COPY = 'real_club_copy', 'Real Club Copy'

    class DirectoryVisibility(models.TextChoices):
        LISTED = 'listed', 'Listed'
        HIDDEN_CODE_ONLY = 'hidden_code_only', 'Hidden Code Only'

    class JoinPolicy(models.TextChoices):
        APPROVAL_REQUIRED = 'approval_required', 'Approval Required'
        INVITE_ONLY = 'invite_only', 'Invite Only'
        SYSTEM_MANAGED = 'system_managed', 'System Managed'

    class VerificationStatus(models.TextChoices):
        NOT_REQUIRED = 'not_required', 'Not Required'
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    name = models.CharField(max_length=100)
    description = models.TextField(blank=False)
    badge = models.ImageField(
        upload_to='../media/clubs/badges/',
        blank=True,
        null=True
    )

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_clubs'
    )
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PRIVATE
    )

    club_type = models.CharField(
        max_length=32,
        choices=ClubType.choices,
        blank=True,
        null=True
    )
    fictional_basis = models.CharField(
        max_length=20,
        choices=FictionalBasis.choices,
        blank=True,
        null=True
    )
    source_real_club_name = models.CharField(
        max_length=150,
        blank=True
    )
    directory_visibility = models.CharField(
        max_length=20,
        choices=DirectoryVisibility.choices,
        blank=True,
        null=True
    )
    join_policy = models.CharField(
        max_length=20,
        choices=JoinPolicy.choices,
        blank=True,
        null=True
    )
    join_code = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        unique=True
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        blank=True,
        null=True
    )
    verification_contact_name = models.CharField(
        max_length=150,
        blank=True
    )
    verification_contact_role = models.CharField(
        max_length=150,
        blank=True
    )
    verification_contact_email = models.EmailField(
        blank=True
    )
    verification_evidence_text = models.TextField(
        blank=True
    )
    verification_evidence_url = models.URLField(
        blank=True
    )

    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(
        max_length=2,
        blank=True,
        help_text='ISO 3166-1 alpha-2 code'
    )
    stadium = models.CharField(max_length=100, blank=True)

    division = models.CharField(
        max_length=100,
        blank=True,
        help_text='League or division name'
    )

    achievements = models.TextField(
        blank=True,
        help_text='Trophies, notable accomplishments'
    )

    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)
    trash_expires_at = models.DateTimeField(null=True, blank=True)
    trashed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trashed_clubs'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['creator']),
            models.Index(fields=['visibility']),
            models.Index(fields=['club_type']),
            models.Index(fields=['directory_visibility']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['creator', 'is_trashed']),
            models.Index(fields=['is_trashed', 'trash_expires_at']),
        ]

    def __str__(self):
        return self.name

    def is_hidden_from_directory(self):
        return self.directory_visibility == self.DirectoryVisibility.HIDDEN_CODE_ONLY

    def requires_verification(self):
        return self.club_type == self.ClubType.USER_REAL_NON_PRO

    def is_system_club(self):
        return self.club_type == self.ClubType.SYSTEM_PROFESSIONAL

    def can_accept_join_requests(self):
        return self.join_policy == self.JoinPolicy.APPROVAL_REQUIRED

    def has_minimal_verification_evidence(self):
        has_contact_name = bool(self.verification_contact_name.strip())
        has_contact_role = bool(self.verification_contact_role.strip())
        has_contact_email = bool(self.verification_contact_email.strip())
        has_evidence = bool(
            self.verification_evidence_text.strip() or self.verification_evidence_url.strip()
        )

        return (
            has_contact_name and
            has_contact_role and
            has_contact_email and
            has_evidence
        )

    def _generate_unique_join_code(self):
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

        for _ in range(20):
            candidate = ''.join(secrets.choice(alphabet) for _ in range(8))
            if not Club.objects.filter(join_code=candidate).exists():
                return candidate

        raise ValueError('Unable to generate a unique club join code.')

    def generate_join_code(self, commit=True):
        if not self.join_code:
            self.join_code = self._generate_unique_join_code()

        if commit and self.pk:
            self.save(update_fields=['join_code'])

        return self.join_code

    def apply_taxonomy_defaults(self):
        if not self.club_type:
            return

        if not self.directory_visibility:
            self.directory_visibility = self.DirectoryVisibility.LISTED

        if self.club_type == self.ClubType.SYSTEM_PROFESSIONAL:
            if not self.join_policy:
                self.join_policy = self.JoinPolicy.SYSTEM_MANAGED
            if not self.verification_status:
                self.verification_status = self.VerificationStatus.NOT_REQUIRED
            return

        if not self.join_policy:
            self.join_policy = self.JoinPolicy.APPROVAL_REQUIRED

        if self.club_type == self.ClubType.USER_REAL_NON_PRO:
            if not self.verification_status:
                self.verification_status = self.VerificationStatus.PENDING
            return

        if self.club_type == self.ClubType.USER_FICTIONAL:
            if not self.verification_status:
                self.verification_status = self.VerificationStatus.NOT_REQUIRED

    def clean(self):
        super().clean()

        errors = {}

        if self.fictional_basis and self.club_type != self.ClubType.USER_FICTIONAL:
            errors['fictional_basis'] = 'fictional_basis is only valid for user_fictional clubs.'

        if self.club_type == self.ClubType.USER_FICTIONAL:
            if not self.fictional_basis:
                errors['fictional_basis'] = 'fictional_basis is required for user_fictional clubs.'
            elif (
                self.fictional_basis == self.FictionalBasis.REAL_CLUB_COPY and
                not self.source_real_club_name.strip()
            ):
                errors['source_real_club_name'] = (
                    'source_real_club_name is required when fictional_basis is real_club_copy.'
                )

        if self.club_type == self.ClubType.USER_REAL_NON_PRO:
            if not self.verification_contact_name.strip():
                errors['verification_contact_name'] = (
                    'verification_contact_name is required for user_real_non_pro clubs.'
                )
            if not self.verification_contact_role.strip():
                errors['verification_contact_role'] = (
                    'verification_contact_role is required for user_real_non_pro clubs.'
                )
            if not self.verification_contact_email.strip():
                errors['verification_contact_email'] = (
                    'verification_contact_email is required for user_real_non_pro clubs.'
                )
            if not (
                self.verification_evidence_text.strip() or
                self.verification_evidence_url.strip()
            ):
                errors['verification_evidence_text'] = (
                    'Provide verification_evidence_text or verification_evidence_url '
                    'for user_real_non_pro clubs.'
                )

        if self.is_system_club() and self.join_policy and self.join_policy != self.JoinPolicy.SYSTEM_MANAGED:
            errors['join_policy'] = 'system_professional clubs must use system_managed join_policy.'

        if (
            self.club_type in {self.ClubType.USER_REAL_NON_PRO, self.ClubType.USER_FICTIONAL} and
            self.join_policy == self.JoinPolicy.SYSTEM_MANAGED
        ):
            errors['join_policy'] = 'system_managed join_policy is only valid for system_professional clubs.'

        if self.is_hidden_from_directory() and not self.join_code and self.pk:
            errors['join_code'] = 'hidden_code_only clubs must have a join_code.'

        if errors:
            raise ValidationError(errors)

    def is_user_managed_club(self):
        return self.club_type in {
            self.ClubType.USER_REAL_NON_PRO,
            self.ClubType.USER_FICTIONAL,
        } or not self.club_type

    def allows_manual_events(self):
        return self.is_user_managed_club()

    def allows_manual_fixtures(self):
        return self.is_user_managed_club()

    def save(self, *args, **kwargs):
        self.apply_taxonomy_defaults()

        if not self.description and self.creator_id:
            self.description = f"{self.creator.email}'s club"

        if self.is_hidden_from_directory() and not self.join_code:
            self.join_code = self._generate_unique_join_code()

        super().save(*args, **kwargs)

    @property
    def is_private(self):
        return self.visibility == self.Visibility.PRIVATE

    @property
    def member_count(self):
        return self.memberships.filter(is_active=True).count()

    @property
    def player_count(self):
        return self.club_players.count()

    def can_be_trashed_by(self, user) -> bool:
        return bool(
            user
            and user.is_authenticated
            and self.creator_id is not None
            and self.creator_id == user.id
        )

    def can_be_restored_by(self, user) -> bool:
        return self.can_be_trashed_by(user)

    def can_be_permanently_deleted_by(self, user) -> bool:
        return self.can_be_trashed_by(user)

    def is_trash_expired(self) -> bool:
        return bool(
            self.is_trashed
            and self.trash_expires_at is not None
            and self.trash_expires_at <= timezone.now()
        )

    def _get_trash_limit(self) -> int:
        return int(getattr(settings, 'CLUB_TRASH_LIMIT_PER_USER', 10))

    def _validate_trash_limit(self):
        limit = self._get_trash_limit()
        active_trashed_count = Club.objects.filter(
            creator_id=self.creator_id,
            is_trashed=True,
        ).exclude(pk=self.pk).count()

        if active_trashed_count >= limit:
            raise ValidationError(
                f'You have reached the club trash limit of {limit} items.'
            )

    def move_to_trash(self, user, commit=True):
        if not self.can_be_trashed_by(user):
            raise ValidationError('Only the club creator can move this club to trash.')

        if self.is_trashed:
            return self

        self._validate_trash_limit()

        now = timezone.now()
        retention_days = int(getattr(settings, 'TRASH_RETENTION_DAYS', 7))

        self.is_trashed = True
        self.trashed_at = now
        self.trash_expires_at = now + timedelta(days=retention_days)
        self.trashed_by = user

        if commit and self.pk:
            self.save(
                update_fields=[
                    'is_trashed',
                    'trashed_at',
                    'trash_expires_at',
                    'trashed_by',
                    'updated_at',
                ]
            )

        return self

    def restore_from_trash(self, user=None, commit=True):
        if user is not None and not self.can_be_restored_by(user):
            raise ValidationError('Only the club creator can restore this club.')

        self.is_trashed = False
        self.trashed_at = None
        self.trash_expires_at = None
        self.trashed_by = None

        if commit and self.pk:
            self.save(
                update_fields=[
                    'is_trashed',
                    'trashed_at',
                    'trash_expires_at',
                    'trashed_by',
                    'updated_at',
                ]
            )

        return self

class ClubMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'          
        ADMIN = 'admin', 'Admin'          
        COACH = 'coach', 'Coach'         
        PLAYER = 'player', 'Player'       
        VIEWER = 'viewer', 'Viewer'        
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='club_memberships'
    )
    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER
    )
    
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_club_invites'
    )
    
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'club']  
        ordering = ['club', 'role', 'joined_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['club', 'role']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.club.name} ({self.role})"
    
    def can_edit_club(self):
        return self.role in [self.Role.OWNER, self.Role.ADMIN]
    
    def can_manage_members(self):
        return self.role in [self.Role.OWNER, self.Role.ADMIN]
    
    def can_create_content(self):
        return self.role in [self.Role.OWNER, self.Role.ADMIN, self.Role.COACH]
    
    def can_view_all_players(self):
        return self.role != self.Role.PLAYER  

class ClubJoinRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'
        CANCELLED = 'cancelled', 'Cancelled'

    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='join_requests'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='club_join_requests'
    )
    requested_role = models.CharField(
        max_length=10,
        choices=ClubMembership.Role.choices,
        default=ClubMembership.Role.PLAYER
    )
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_club_join_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    selected_club_player = models.ForeignKey(
        'ClubPlayer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='join_request_selections'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['club', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['club', 'requested_role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['club', 'user'],
                condition=models.Q(status='pending'),
                name='unique_pending_join_request_per_user_club'
            )
        ]

    def __str__(self):
        return f'{self.user.email} -> {self.club.name} ({self.requested_role}, {self.status})'

    def is_pending(self):
        return self.status == self.Status.PENDING

    def can_be_reviewed(self):
        return self.is_pending()

    def can_be_withdrawn(self):
        return self.is_pending()

    def clean(self):
        super().clean()

        errors = {}
        is_pending = self.status == self.Status.PENDING

        if self.club_id and self.club.join_policy != Club.JoinPolicy.APPROVAL_REQUIRED:
            errors['club'] = 'Join requests are only allowed for clubs using approval_required join policy.'

        if self.club_id and self.club.is_system_club():
            errors['club'] = 'Join requests are not allowed for system-managed clubs.'

        if self.requested_role != ClubMembership.Role.PLAYER:
            errors['requested_role'] = 'Phase B self-request flow only supports player membership requests.'

        if is_pending and self.club_id and self.user_id:
            if ClubMembership.objects.filter(
                club=self.club,
                user=self.user,
                is_active=True
            ).exists():
                errors['user'] = 'This user is already an active member of the club.'

        if is_pending and self.selected_club_player_id:
            if self.requested_role != ClubMembership.Role.PLAYER:
                errors['selected_club_player'] = 'Roster linking is only valid for player join requests.'
            elif self.selected_club_player.club_id != self.club_id:
                errors['selected_club_player'] = 'Selected ClubPlayer must belong to the same club.'
            elif self.selected_club_player.user_id is not None:
                errors['selected_club_player'] = 'Selected ClubPlayer is already claimed by a user.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean(validate_constraints=False)
        return super().save(*args, **kwargs)

    def create_membership_from_request(self, granted_by=None):
        membership, _ = ClubMembership.objects.get_or_create(
            user=self.user,
            club=self.club,
            defaults={
                'role': self.requested_role,
                'is_active': True,
                'invited_by': granted_by,
            }
        )

        if not membership.is_active or membership.role != self.requested_role:
            membership.role = self.requested_role
            membership.is_active = True
            if granted_by is not None:
                membership.invited_by = granted_by
            membership.save(update_fields=['role', 'is_active', 'invited_by', 'updated_at'])

        return membership

    def mark_approved(self, reviewed_by, review_note='', selected_club_player=None):
        if not self.can_be_reviewed():
            raise ValidationError('Only pending join requests can be approved.')

        if selected_club_player is not None:
            self.selected_club_player = selected_club_player

        self.full_clean()

        with transaction.atomic():
            if self.selected_club_player is not None:
                self.selected_club_player.user = self.user
                self.selected_club_player.claimed_at = timezone.now()
                self.selected_club_player.claim_token = None
                self.selected_club_player.save(
                    update_fields=['user', 'claimed_at', 'claim_token', 'updated_at']
                )

            membership = self.create_membership_from_request(granted_by=reviewed_by)

            self.status = self.Status.APPROVED
            self.reviewed_by = reviewed_by
            self.reviewed_at = timezone.now()
            self.review_note = review_note
            self.save(update_fields=[
                'status',
                'reviewed_by',
                'reviewed_at',
                'review_note',
                'selected_club_player',
                'updated_at',
            ])

        return membership

    def mark_rejected(self, reviewed_by, review_note=''):
        if not self.can_be_reviewed():
            raise ValidationError('Only pending join requests can be rejected.')

        self.status = self.Status.REJECTED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_note = review_note
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_note', 'updated_at'])

    def mark_withdrawn(self):
        if not self.can_be_withdrawn():
            raise ValidationError('Only pending join requests can be withdrawn.')

        self.status = self.Status.WITHDRAWN
        self.save(update_fields=['status', 'updated_at'])

    def mark_cancelled(self, reviewed_by=None, review_note=''):
        if not self.is_pending():
            raise ValidationError('Only pending join requests can be cancelled.')

        self.status = self.Status.CANCELLED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now() if reviewed_by else None
        self.review_note = review_note
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_note', 'updated_at'])


class ClubInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        REVOKED = 'revoked', 'Revoked'
        EXPIRED = 'expired', 'Expired'

    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_club_invitations'
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_club_invitations'
    )
    invited_role = models.CharField(
        max_length=10,
        choices=ClubMembership.Role.choices,
        default=ClubMembership.Role.PLAYER
    )
    note = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    response_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['club', 'status']),
            models.Index(fields=['invited_user', 'status']),
            models.Index(fields=['club', 'invited_role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['club', 'invited_user', 'invited_role'],
                condition=models.Q(status='pending'),
                name='unique_pending_invitation_per_user_club_role'
            )
        ]

    def __str__(self):
        return f'{self.invited_user.email} <- {self.club.name} ({self.invited_role}, {self.status})'

    def is_pending(self):
        return self.status == self.Status.PENDING

    def can_be_reviewed(self):
        return self.is_pending()

    def can_be_revoked(self):
        return self.is_pending()

    def clean(self):
        super().clean()

        errors = {}
        is_pending = self.status == self.Status.PENDING

        if self.invited_role == ClubMembership.Role.OWNER:
            errors['invited_role'] = 'Owner role cannot be assigned through the invitation workflow.'

        if is_pending and self.club_id and self.invited_user_id:
            if ClubMembership.objects.filter(
                club=self.club,
                user=self.invited_user,
                is_active=True
            ).exists():
                errors['invited_user'] = 'This user is already an active member of the club.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean(validate_constraints=False)
        return super().save(*args, **kwargs)

    def create_membership_from_invite(self):
        membership, _ = ClubMembership.objects.get_or_create(
            user=self.invited_user,
            club=self.club,
            defaults={
                'role': self.invited_role,
                'is_active': True,
                'invited_by': self.invited_by,
            }
        )

        if not membership.is_active or membership.role != self.invited_role:
            membership.role = self.invited_role
            membership.is_active = True
            membership.invited_by = self.invited_by
            membership.save(update_fields=['role', 'is_active', 'invited_by', 'updated_at'])

        return membership

    def mark_accepted(self, response_note=''):
        if not self.can_be_reviewed():
            raise ValidationError('Only pending invitations can be accepted.')

        with transaction.atomic():
            membership = self.create_membership_from_invite()

            self.status = self.Status.ACCEPTED
            self.responded_at = timezone.now()
            self.response_note = response_note
            self.save(update_fields=['status', 'responded_at', 'response_note', 'updated_at'])

        return membership

    def mark_declined(self, response_note=''):
        if not self.can_be_reviewed():
            raise ValidationError('Only pending invitations can be declined.')

        self.status = self.Status.DECLINED
        self.responded_at = timezone.now()
        self.response_note = response_note
        self.save(update_fields=['status', 'responded_at', 'response_note', 'updated_at'])

    def mark_revoked(self, response_note=''):
        if not self.can_be_revoked():
            raise ValidationError('Only pending invitations can be revoked.')

        self.status = self.Status.REVOKED
        self.responded_at = timezone.now()
        self.response_note = response_note
        self.save(update_fields=['status', 'responded_at', 'response_note', 'updated_at'])
             
class ClubPlayer(models.Model):
    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='club_players'
    )

    player = models.ForeignKey(
        'players.Player',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='club_memberships'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='club_players'
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    display_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Nickname or preferred name"
    )

    squad_number = models.PositiveSmallIntegerField(null=True, blank=True)
    primary_position = models.CharField(max_length=4, choices=Position.choices, blank=True)
    secondary_position = models.CharField(max_length=4, choices=Position.choices, blank=True)
    preferred_foot = models.CharField(max_length=1, choices=PreferredFoot.choices, blank=True)

    date_of_birth = models.DateField(null=True, blank=True)
    height_cm = models.PositiveSmallIntegerField(null=True, blank=True)

    photo = models.ImageField(
        upload_to='players/photos/',
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Active in current squad"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="If true, this player profile can be used by other public clubs"
    )

    claim_token = models.CharField(
        max_length=64,
        blank=True,
        unique=True,
        null=True,
        help_text="Token for claiming this profile"
    )
    claimed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_club_players'
    )

    class Meta:
        ordering = ['squad_number', 'last_name', 'first_name', 'id']
        indexes = [
            models.Index(fields=['club', 'is_active']),
            models.Index(fields=['user']),
            models.Index(fields=['claim_token']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['club', 'squad_number'],
                condition=models.Q(squad_number__isnull=False),
                name='unique_squad_number_per_club'
            )
        ]

    def __str__(self):
        if self.player_id:
            name = self.player.display_name or self.player.full_name
        else:
            name = self.display_name or f"{self.first_name} {self.last_name}".strip()
        return f"{name} ({self.club.name})"

    @property
    def is_claimed(self):
        return self.user is not None

    @property
    def full_name(self):
        if self.player_id:
            return self.player.full_name
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_linked_to_player(self):
        return self.player_id is not None

    def can_link_to_player(self, player, *, allow_relink=False):
        if player is None:
            raise ValidationError({'player': 'A canonical Player is required.'})

        if not isinstance(player, Player):
            raise ValidationError({'player': 'Expected a canonical Player instance.'})

        if self.player_id and self.player_id != player.id and not allow_relink:
            raise ValidationError({
                'player': (
                    'This club player is already linked to a different canonical Player. '
                    'Use an explicit relink flow.'
                )
            })

        return True

    def link_to_player(self, player, *, commit=True):
        self.can_link_to_player(player)

        if self.player_id == player.id:
            return self

        self.player = player

        if commit:
            self.save(update_fields=['player', 'updated_at'])

        return self

    def unlink_player(self, *, commit=True):
        if not self.player_id:
            return self

        self.player = None

        if commit:
            self.save(update_fields=['player', 'updated_at'])

        return self

    def relink_player(self, player, *, commit=True):
        self.can_link_to_player(player, allow_relink=True)

        if self.player_id == player.id:
            return self

        self.player = player

        if commit:
            self.save(update_fields=['player', 'updated_at'])

        return self

    def get_display_player_identity(self):
        if self.player_id:
            return {
                'is_linked_to_player': True,
                'player_id': self.player_id,
                'first_name': self.player.first_name,
                'last_name': self.player.last_name,
                'full_name': self.player.full_name,
                'display_name': self.player.display_name or '',
                'primary_position': self.player.primary_position or '',
                'secondary_positions': list(self.player.secondary_positions or []),
                'preferred_foot': self.player.preferred_foot or '',
                'date_of_birth': self.player.date_of_birth,
                'height_cm': self.player.height_cm,
                'nationality': self.player.nationality or '',
                'photo': self.player.photo,
            }

        return {
            'is_linked_to_player': False,
            'player_id': None,
            'first_name': self.first_name or '',
            'last_name': self.last_name or '',
            'full_name': f'{self.first_name} {self.last_name}'.strip(),
            'display_name': self.display_name or '',
            'primary_position': self.primary_position or '',
            'secondary_positions': [self.secondary_position] if self.secondary_position else [],
            'preferred_foot': self.preferred_foot or '',
            'date_of_birth': self.date_of_birth,
            'height_cm': self.height_cm,
            'nationality': '',
            'photo': self.photo,
        }

    def generate_claim_token(self):
        import secrets
        self.claim_token = secrets.token_urlsafe(32)
        self.save(update_fields=['claim_token'])
        return self.claim_token

    def claim(self, user):
        from django.utils import timezone

        self.user = user
        self.claimed_at = timezone.now()
        self.claim_token = None
        self.save(update_fields=['user', 'claimed_at', 'claim_token'])

        ClubMembership.objects.get_or_create(
            user=user,
            club=self.club,
            defaults={'role': ClubMembership.Role.PLAYER}
        )
        

class ClubExternalIdentity(models.Model):
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="external_identities",
    )
    provider = models.CharField(
        max_length=50,
        choices=ExternalProvider.choices,
    )
    external_id = models.CharField(max_length=100)
    provider_display_name = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)
    competition_context = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "external_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_id"],
                name="uniq_club_ext_identity_provider_external_id",
            ),
        ]
        indexes = [
            models.Index(fields=["club", "provider"]),
            models.Index(fields=["provider", "external_id"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.external_id} -> {self.club}"


class Season(models.Model):
    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='seasons'
    )
    
    name = models.CharField(
        max_length=20,
        help_text="e.g., '2024/2025'"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    
    matches_played = models.PositiveSmallIntegerField(default=0)
    wins = models.PositiveSmallIntegerField(default=0)
    draws = models.PositiveSmallIntegerField(default=0)
    losses = models.PositiveSmallIntegerField(default=0)
    goals_for = models.PositiveSmallIntegerField(default=0)
    goals_against = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        ordering = ['-start_date']
        unique_together = ['club', 'name']
        indexes = [
            models.Index(fields=['club', 'is_current']),
        ]
    
    def __str__(self):
        return f"{self.club.name} - {self.name}"
    
    @property
    def goal_difference(self):
        return self.goals_for - self.goals_against
    
    @property
    def points(self):
        return (self.wins * 3) + self.draws
    
    def save(self, *args, **kwargs):
        if self.is_current:
            Season.objects.filter(
                club=self.club, 
                is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class PlayerSeasonStats(models.Model):
    player = models.ForeignKey(
        'ClubPlayer',
        on_delete=models.CASCADE,
        related_name='season_stats'
    )
    season = models.ForeignKey(
        'Season',
        on_delete=models.CASCADE,
        related_name='player_stats'
    )
    
    appearances = models.PositiveSmallIntegerField(default=0)
    starts = models.PositiveSmallIntegerField(default=0)
    minutes_played = models.PositiveIntegerField(default=0)
    
    goals = models.PositiveSmallIntegerField(default=0)
    assists = models.PositiveSmallIntegerField(default=0)
    shots = models.PositiveSmallIntegerField(default=0)
    shots_on_target = models.PositiveSmallIntegerField(default=0)
    
    tackles = models.PositiveSmallIntegerField(default=0)
    interceptions = models.PositiveSmallIntegerField(default=0)
    clearances = models.PositiveSmallIntegerField(default=0)
    
    yellow_cards = models.PositiveSmallIntegerField(default=0)
    red_cards = models.PositiveSmallIntegerField(default=0)
    
    passes_attempted = models.PositiveIntegerField(default=0)
    passes_completed = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['player', 'season']
        ordering = ['-season__start_date']
    
    def __str__(self):
        return f"{self.player} - {self.season.name}"
    
    @property
    def pass_completion_rate(self):
        if self.passes_attempted == 0:
            return 0.0
        return round(self.passes_completed / self.passes_attempted * 100, 1)
    
    @property
    def minutes_per_goal(self):
        if self.goals == 0:
            return None
        return round(self.minutes_played / self.goals, 1)

class ClubEvent(models.Model):
    class EventType(models.TextChoices):
        TRAINING = 'training', 'Training'
        MEETING = 'meeting', 'Meeting'
        SOCIAL = 'social', 'Social'
        ANALYSIS = 'analysis', 'Analysis'
        OTHER = 'other', 'Other'

    class SourceType(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        SYSTEM = 'system', 'System'
        PROVIDER = 'provider', 'Provider'

    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='events'
    )
    title = models.CharField(max_length=200)
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.OTHER
    )
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=200, blank=True)
    is_mandatory = models.BooleanField(default=False)
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.MANUAL
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_club_events'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_datetime', 'id']
        indexes = [
            models.Index(fields=['club', 'start_datetime']),
            models.Index(fields=['club', 'source_type']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f'{self.title} - {self.club.name}'

    @classmethod
    def can_be_manually_created_for_club(cls, club):
        return bool(club and club.allows_manual_events())

    def is_system_managed_item(self):
        return self.source_type in {
            self.SourceType.SYSTEM,
            self.SourceType.PROVIDER,
        }

    def is_user_editable(self):
        return (
            self.source_type == self.SourceType.MANUAL and
            self.club.allows_manual_events()
        )

    def is_future_item(self):
        return self.start_datetime >= timezone.now()

    def get_calendar_label(self):
        return self.title

    def clean(self):
        super().clean()

        errors = {}

        if self.title and not self.title.strip():
            errors['title'] = 'title cannot be blank or whitespace only.'

        if self.end_datetime and self.end_datetime < self.start_datetime:
            errors['end_datetime'] = 'end_datetime must be after start_datetime.'

        if self.source_type == self.SourceType.MANUAL and not self.club.allows_manual_events():
            errors['source_type'] = (
                'Manual club events are only allowed for user-managed clubs.'
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean(validate_constraints=False)
        return super().save(*args, **kwargs)

class Fixture(models.Model):
    class Venue(models.TextChoices):
        HOME = 'home', 'Home'
        AWAY = 'away', 'Away'
        NEUTRAL = 'neutral', 'Neutral'

    class FixtureStatus(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        COMPLETED = 'completed', 'Completed'
        POSTPONED = 'postponed', 'Postponed'
        CANCELLED = 'cancelled', 'Cancelled'

    class SourceType(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        SYSTEM = 'system', 'System'
        PROVIDER = 'provider', 'Provider'

    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='fixtures'
    )
    opponent_name = models.CharField(max_length=100)
    venue = models.CharField(
        max_length=10,
        choices=Venue.choices
    )
    competition = models.CharField(
        max_length=100,
        blank=True,
        help_text='League, cup, friendly, or other competition label.'
    )
    match_datetime = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    fixture_status = models.CharField(
        max_length=20,
        choices=FixtureStatus.choices,
        default=FixtureStatus.SCHEDULED
    )
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.MANUAL
    )
    external_fixture_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Provider or system fixture identifier for future sync paths.'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_club_fixtures'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['match_datetime', 'id']
        indexes = [
            models.Index(fields=['club', 'match_datetime']),
            models.Index(fields=['club', 'fixture_status']),
            models.Index(fields=['club', 'source_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['club', 'external_fixture_id'],
                condition=~models.Q(external_fixture_id=''),
                name='unique_nonblank_external_fixture_id_per_club',
            ),
        ]

    def __str__(self):
        connector = 'vs'
        if self.venue == self.Venue.AWAY:
            connector = '@'
        return f'{self.club.name} {connector} {self.opponent_name} ({self.match_datetime:%Y-%m-%d %H:%M})'

    @classmethod
    def can_be_manually_created_for_club(cls, club):
        return bool(club and club.allows_manual_fixtures())

    def is_system_managed_item(self):
        return self.source_type in {
            self.SourceType.SYSTEM,
            self.SourceType.PROVIDER,
        }

    def is_user_editable(self):
        return (
            self.source_type == self.SourceType.MANUAL and
            self.club.allows_manual_fixtures()
        )

    def is_future_item(self):
        return self.match_datetime >= timezone.now()

    def get_calendar_label(self):
        if self.venue == self.Venue.HOME:
            return f'vs {self.opponent_name}'
        if self.venue == self.Venue.AWAY:
            return f'@ {self.opponent_name}'
        return f'vs {self.opponent_name}'

    def clean(self):
        super().clean()

        errors = {}

        if self.opponent_name and not self.opponent_name.strip():
            errors['opponent_name'] = 'opponent_name cannot be blank or whitespace only.'

        if self.source_type == self.SourceType.MANUAL and not self.club.allows_manual_fixtures():
            errors['source_type'] = (
                'Manual fixtures are only allowed for user-managed clubs.'
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean(validate_constraints=False)
        return super().save(*args, **kwargs)

class ClubResource(models.Model):
    class FileKind(models.TextChoices):
        PDF = 'pdf', 'PDF'
        DOCX = 'docx', 'DOCX'
        PPTX = 'pptx', 'PPTX'
        XLSX = 'xlsx', 'XLSX'
        CSV = 'csv', 'CSV'
        IMAGE = 'image', 'Image'

    class StorageBackend(models.TextChoices):
        LOCAL = 'local', 'Local'
        CLOUDINARY = 'cloudinary', 'Cloudinary'

    class EngagementVisibility(models.TextChoices):
        STAFF_ONLY = 'staff_only', 'Staff Only'
        CLUB_VISIBLE = 'club_visible', 'Club Visible'

    MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

    SUPPORTED_MIME_TYPES = {
        FileKind.PDF: {'application/pdf'},
        FileKind.DOCX: {
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        },
        FileKind.PPTX: {
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        },
        FileKind.XLSX: {
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        },
        FileKind.CSV: {
            'text/csv',
            'application/csv',
            'application/vnd.ms-excel',
        },
        FileKind.IMAGE: {
            'image/png',
            'image/jpeg',
            'image/webp',
        },
    }

    SUPPORTED_EXTENSIONS = {
        FileKind.PDF: {'pdf'},
        FileKind.DOCX: {'docx'},
        FileKind.PPTX: {'pptx'},
        FileKind.XLSX: {'xlsx'},
        FileKind.CSV: {'csv'},
        FileKind.IMAGE: {'png', 'jpg', 'jpeg', 'webp'},
    }

    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='resources',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_club_resources',
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    file = models.FileField(upload_to='clubs/resources/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=255)
    file_size_bytes = models.PositiveBigIntegerField()

    file_kind = models.CharField(
        max_length=16,
        choices=FileKind.choices,
    )

    storage_backend = models.CharField(
        max_length=20,
        choices=StorageBackend.choices,
        default=StorageBackend.LOCAL,
    )
    storage_key = models.CharField(
        max_length=500,
        blank=True,
        help_text='Generic storage identifier such as a Cloudinary public ID or local storage key.',
    )

    engagement_visibility = models.CharField(
        max_length=20,
        choices=EngagementVisibility.choices,
        default=EngagementVisibility.STAFF_ONLY,
    )
    is_archived = models.BooleanField(default=False)

    total_pages = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='PDF page count where known.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['club', 'is_archived']),
            models.Index(fields=['club', 'file_kind']),
            models.Index(fields=['club', 'engagement_visibility']),
            models.Index(fields=['storage_backend']),
        ]

    def __str__(self):
        return f'{self.title} ({self.club.name})'

    def get_normalised_mime_type(self):
        return (self.mime_type or '').split(';')[0].strip().lower()

    def get_extension(self):
        filename = (self.original_filename or '').strip()
        if '.' not in filename:
            return ''
        return filename.rsplit('.', 1)[1].lower()

    def is_pdf(self):
        return self.file_kind == self.FileKind.PDF

    def is_image(self):
        return self.file_kind == self.FileKind.IMAGE

    def can_inline_view(self):
        return self.is_pdf()

    def is_download_only(self):
        return not self.can_inline_view()

    def archive(self, commit=True):
        self.is_archived = True
        if commit and self.pk:
            self.save(update_fields=['is_archived', 'updated_at'])
        return self

    def unarchive(self, commit=True):
        self.is_archived = False
        if commit and self.pk:
            self.save(update_fields=['is_archived', 'updated_at'])
        return self

    def clean(self):
        super().clean()

        errors = {}

        normalised_mime_type = self.get_normalised_mime_type()
        extension = self.get_extension()

        allowed_mime_types = self.SUPPORTED_MIME_TYPES.get(self.file_kind, set())
        allowed_extensions = self.SUPPORTED_EXTENSIONS.get(self.file_kind, set())

        if not self.original_filename.strip():
            errors['original_filename'] = 'original_filename is required.'

        if not normalised_mime_type:
            errors['mime_type'] = 'mime_type is required.'
        elif normalised_mime_type not in allowed_mime_types:
            errors['mime_type'] = (
                f'Unsupported MIME type for {self.file_kind}. '
                f'Allowed values: {", ".join(sorted(allowed_mime_types))}.'
            )

        if not extension:
            errors['original_filename'] = 'A supported file extension is required.'
        elif extension not in allowed_extensions:
            errors['original_filename'] = (
                f'Unsupported file extension for {self.file_kind}. '
                f'Allowed values: {", ".join(sorted(allowed_extensions))}.'
            )

        if self.file_size_bytes > self.MAX_FILE_SIZE_BYTES:
            errors['file_size_bytes'] = (
                f'File size exceeds the {self.MAX_FILE_SIZE_BYTES} byte limit.'
            )

        if self.total_pages is not None and not self.is_pdf():
            errors['total_pages'] = 'total_pages is only valid for PDF resources.'

        if self.is_pdf() and self.total_pages is not None and self.total_pages < 1:
            errors['total_pages'] = 'PDF total_pages must be at least 1 when provided.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean(validate_constraints=False)
        return super().save(*args, **kwargs)


class ClubResourceView(models.Model):
    MAX_ACTIVE_SECONDS_DELTA = 120
    MIN_PDF_COMPLETION_ACTIVE_SECONDS = 30
    MIN_NON_PDF_COMPLETION_ACTIVE_SECONDS = 10

    resource = models.ForeignKey(
        'ClubResource',
        on_delete=models.CASCADE,
        related_name='view_summaries',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='club_resource_views',
    )

    first_opened_at = models.DateTimeField(null=True, blank=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)

    total_active_seconds = models.PositiveIntegerField(default=0)
    highest_page_reached = models.PositiveIntegerField(default=0)

    opened = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['resource_id', 'user_id']
        constraints = [
            models.UniqueConstraint(
                fields=['resource', 'user'],
                name='unique_club_resource_view_per_user',
            ),
        ]
        indexes = [
            models.Index(fields=['resource', 'completed']),
            models.Index(fields=['resource', 'last_opened_at']),
            models.Index(fields=['user', 'opened']),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.resource.title}'

    def record_opened(self, opened_at=None):
        opened_at = opened_at or timezone.now()

        if self.first_opened_at is None:
            self.first_opened_at = opened_at

        self.last_opened_at = opened_at
        self.opened = True
        return self

    def recalculate_completed(self):
        if self.resource.is_pdf():
            if not self.resource.total_pages:
                self.completed = False
                return self.completed

            self.completed = (
                self.highest_page_reached >= self.resource.total_pages and
                self.total_active_seconds >= self.MIN_PDF_COMPLETION_ACTIVE_SECONDS
            )
            return self.completed

        self.completed = (
            self.opened and
            self.total_active_seconds >= self.MIN_NON_PDF_COMPLETION_ACTIVE_SECONDS
        )
        return self.completed

    def update_progress(self, active_seconds_delta=0, page_reached=None, opened_at=None):
        self.record_opened(opened_at=opened_at)

        safe_delta = int(active_seconds_delta or 0)
        safe_delta = max(0, min(safe_delta, self.MAX_ACTIVE_SECONDS_DELTA))
        self.total_active_seconds += safe_delta

        if page_reached is not None and self.resource.is_pdf():
            safe_page = max(0, int(page_reached))
            if self.resource.total_pages:
                safe_page = min(safe_page, self.resource.total_pages)
            self.highest_page_reached = max(self.highest_page_reached, safe_page)

        self.recalculate_completed()
        return self

    def clean(self):
        super().clean()

        errors = {}

        if self.opened and self.first_opened_at is None:
            errors['first_opened_at'] = 'first_opened_at is required once opened becomes True.'

        if self.opened and self.last_opened_at is None:
            errors['last_opened_at'] = 'last_opened_at is required once opened becomes True.'

        if self.last_opened_at and self.first_opened_at and self.last_opened_at < self.first_opened_at:
            errors['last_opened_at'] = 'last_opened_at cannot be earlier than first_opened_at.'

        if self.completed and not self.opened:
            errors['completed'] = 'completed cannot be True when opened is False.'

        if not self.resource.is_pdf() and self.highest_page_reached > 0:
            errors['highest_page_reached'] = (
                'highest_page_reached is only valid for PDF resources.'
            )

        if (
            self.resource.is_pdf() and
            self.resource.total_pages and
            self.highest_page_reached > self.resource.total_pages
        ):
            errors['highest_page_reached'] = (
                'highest_page_reached cannot exceed the resource total_pages.'
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.recalculate_completed()
        self.full_clean(validate_constraints=False)
        return super().save(*args, **kwargs)

class ClubImportJob(models.Model):
    class ImportType(models.TextChoices):
        PLAYER_PROFILE_UPDATE = 'player_profile_update', 'Player Profile Update'
        PLAYER_SEASON_STATS = 'player_season_stats', 'Player Season Stats'
        SQUAD_METRICS = 'squad_metrics', 'Squad Metrics'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        UPLOADED = 'uploaded', 'Uploaded'
        VALIDATING = 'validating', 'Validating'
        PREVIEW_READY = 'preview_ready', 'Preview Ready'
        CONFIRMED = 'confirmed', 'Confirmed'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='import_jobs',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_club_import_jobs',
    )
    source_resource = models.ForeignKey(
        'ClubResource',
        on_delete=models.PROTECT,
        related_name='import_jobs',
    )

    import_type = models.CharField(
        max_length=32,
        choices=ImportType.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )

    row_count = models.PositiveIntegerField(default=0)
    valid_row_count = models.PositiveIntegerField(default=0)
    imported_row_count = models.PositiveIntegerField(default=0)
    skipped_row_count = models.PositiveIntegerField(default=0)
    failed_row_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)

    error_summary = models.JSONField(default=dict, blank=True)
    preview_payload = models.JSONField(default=dict, blank=True)
    report_payload = models.JSONField(default=dict, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['club', 'status']),
            models.Index(fields=['club', 'import_type']),
            models.Index(fields=['source_resource']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.club.name} | {self.import_type} | {self.status}'

    @property
    def is_terminal(self):
        return self.status in {
            self.Status.COMPLETED,
            self.Status.FAILED,
            self.Status.CANCELLED,
        }

    def can_be_cancelled(self):
        return not self.is_terminal

    def clean(self):
        super().clean()

        errors = {}

        if self.source_resource_id and self.club_id:
            if self.source_resource.club_id != self.club_id:
                errors['source_resource'] = (
                    'source_resource must belong to the same club as the import job.'
                )

            if self.source_resource.file_kind not in {
                ClubResource.FileKind.CSV,
                ClubResource.FileKind.XLSX,
            }:
                errors['source_resource'] = (
                    'source_resource must be a CSV or XLSX ClubResource.'
                )

        if self.completed_at and self.started_at and self.completed_at < self.started_at:
            errors['completed_at'] = 'completed_at cannot be earlier than started_at.'

        if self.status == self.Status.COMPLETED and self.completed_at is None:
            errors['completed_at'] = 'completed_at is required when status is completed.'

        if (
            self.status in {
                self.Status.UPLOADED,
                self.Status.VALIDATING,
                self.Status.PREVIEW_READY,
                self.Status.CONFIRMED,
                self.Status.PROCESSING,
            }
            and self.completed_at is not None
        ):
            errors['completed_at'] = (
                'completed_at must be empty until the job reaches a terminal state.'
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean(validate_constraints=False)
        return super().save(*args, **kwargs)

    def mark_validating(self, commit=True):
        self.status = self.Status.VALIDATING
        if self.started_at is None:
            self.started_at = timezone.now()
        self.completed_at = None

        if commit and self.pk:
            self.save(update_fields=[
                'status',
                'started_at',
                'completed_at',
                'updated_at',
            ])

        return self

    def mark_preview_ready(
        self,
        *,
        preview_payload,
        row_count,
        valid_row_count,
        warning_count=0,
        commit=True,
    ):
        self.status = self.Status.PREVIEW_READY
        if self.started_at is None:
            self.started_at = timezone.now()

        self.completed_at = None
        self.preview_payload = preview_payload or {}
        self.row_count = row_count
        self.valid_row_count = valid_row_count
        self.warning_count = warning_count

        # Preview stage is pre-commit, so final outcome counts stay reset.
        self.imported_row_count = 0
        self.skipped_row_count = 0
        self.failed_row_count = 0
        self.error_summary = {}

        if commit and self.pk:
            self.save(update_fields=[
                'status',
                'started_at',
                'completed_at',
                'preview_payload',
                'row_count',
                'valid_row_count',
                'warning_count',
                'imported_row_count',
                'skipped_row_count',
                'failed_row_count',
                'error_summary',
                'updated_at',
            ])

        return self

    def mark_failed(
        self,
        *,
        error_summary,
        report_payload=None,
        clear_preview=True,
        commit=True,
    ):
        self.status = self.Status.FAILED
        if self.started_at is None:
            self.started_at = timezone.now()
        self.completed_at = timezone.now()
        self.error_summary = error_summary or {}
        self.report_payload = report_payload or {}

        if clear_preview:
            self.preview_payload = {}

        if commit and self.pk:
            update_fields = [
                'status',
                'started_at',
                'completed_at',
                'error_summary',
                'report_payload',
                'updated_at',
            ]
            if clear_preview:
                update_fields.append('preview_payload')

            self.save(update_fields=update_fields)

        return self

    def set_report_payload(self, *, report_payload, commit=True):
        self.report_payload = report_payload or {}

        if commit and self.pk:
            self.save(update_fields=[
                'report_payload',
                'updated_at',
            ])

        return self

    def mark_confirmed(self, commit=True):
        self.status = self.Status.CONFIRMED
        if self.started_at is None:
            self.started_at = timezone.now()
        self.completed_at = None

        if commit and self.pk:
            self.save(update_fields=[
                'status',
                'started_at',
                'completed_at',
                'updated_at',
            ])

        return self

    def mark_processing(self, commit=True):
        self.status = self.Status.PROCESSING
        if self.started_at is None:
            self.started_at = timezone.now()
        self.completed_at = None

        if commit and self.pk:
            self.save(update_fields=[
                'status',
                'started_at',
                'completed_at',
                'updated_at',
            ])

        return self

    def mark_completed(
        self,
        *,
        imported_row_count,
        skipped_row_count,
        failed_row_count,
        report_payload,
        commit=True,
    ):
        self.status = self.Status.COMPLETED
        if self.started_at is None:
            self.started_at = timezone.now()
        self.completed_at = timezone.now()

        self.imported_row_count = imported_row_count
        self.skipped_row_count = skipped_row_count
        self.failed_row_count = failed_row_count
        self.error_summary = {}
        self.report_payload = report_payload or {}

        if commit and self.pk:
            self.save(update_fields=[
                'status',
                'started_at',
                'completed_at',
                'imported_row_count',
                'skipped_row_count',
                'failed_row_count',
                'error_summary',
                'report_payload',
                'updated_at',
            ])

        return self

    def mark_commit_failed(
        self,
        *,
        imported_row_count,
        skipped_row_count,
        failed_row_count,
        error_summary,
        report_payload,
        commit=True,
    ):
        self.status = self.Status.FAILED
        if self.started_at is None:
            self.started_at = timezone.now()
        self.completed_at = timezone.now()

        self.imported_row_count = imported_row_count
        self.skipped_row_count = skipped_row_count
        self.failed_row_count = failed_row_count
        self.error_summary = error_summary or {}
        self.report_payload = report_payload or {}

        if commit and self.pk:
            self.save(update_fields=[
                'status',
                'started_at',
                'completed_at',
                'imported_row_count',
                'skipped_row_count',
                'failed_row_count',
                'error_summary',
                'report_payload',
                'updated_at',
            ])

        return self