from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone


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
        app_label = 'clubs'
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


class ClubFan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='club_follows'
    )
    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='fans'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'clubs'
        unique_together = ['user', 'club']
        ordering = ['club', 'created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['club', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} follows {self.club.name}"


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
        app_label = 'clubs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['club', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['club', 'requested_role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['club', 'user'],
                condition=Q(status='pending'),
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
        from .club import Club
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
        app_label = 'clubs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['club', 'status']),
            models.Index(fields=['invited_user', 'status']),
            models.Index(fields=['club', 'invited_role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['club', 'invited_user', 'invited_role'],
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
