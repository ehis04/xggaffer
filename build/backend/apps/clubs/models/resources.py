from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


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
        app_label = 'clubs'
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
        app_label = 'clubs'
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
