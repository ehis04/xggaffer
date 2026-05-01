import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


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
        app_label = 'clubs'
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

    @property
    def fan_count(self):
        return self.fans.count()

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
        # Active players represent the live squad for the current season context.
        return self.club_players.filter(is_active=True).count()

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
