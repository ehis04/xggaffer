from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


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
        app_label = 'clubs'
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
        from .resources import ClubResource
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
