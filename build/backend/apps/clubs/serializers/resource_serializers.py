from rest_framework import serializers

from ..models import ClubMembership, ClubResource, ClubResourceView
from ..storage import (
    ClubResourceStorageError,
    cloudinary_resources_enabled,
    upload_club_resource_to_cloudinary,
)


def _normalise_uploaded_resource_file(uploaded_file):
    if uploaded_file is None:
        raise serializers.ValidationError({'file': 'A file upload is required.'})

    original_filename = (getattr(uploaded_file, 'name', '') or '').strip()
    mime_type = (getattr(uploaded_file, 'content_type', '') or '').split(';')[0].strip().lower()
    file_size_bytes = int(getattr(uploaded_file, 'size', 0) or 0)

    if not original_filename:
        raise serializers.ValidationError({'file': 'Uploaded file must include a filename.'})

    if not mime_type:
        raise serializers.ValidationError({'file': 'Uploaded file content type is missing or unsupported.'})

    if file_size_bytes > ClubResource.MAX_FILE_SIZE_BYTES:
        raise serializers.ValidationError({
            'file': f'File exceeds the {ClubResource.MAX_FILE_SIZE_BYTES} byte limit.',
        })

    extension = ''
    if '.' in original_filename:
        extension = original_filename.rsplit('.', 1)[1].lower()

    matched_kind = None
    for file_kind, mime_types in ClubResource.SUPPORTED_MIME_TYPES.items():
        allowed_extensions = ClubResource.SUPPORTED_EXTENSIONS.get(file_kind, set())
        if mime_type in mime_types and extension in allowed_extensions:
            matched_kind = file_kind
            break

    if matched_kind is None:
        raise serializers.ValidationError({
            'file': (
                'Unsupported file type. Supported formats are PDF, DOCX, PPTX, '
                'XLSX, CSV, PNG, JPG, JPEG, and WEBP.'
            )
        })

    return {
        'original_filename': original_filename,
        'mime_type': mime_type,
        'file_size_bytes': file_size_bytes,
        'file_kind': matched_kind,
    }


class ClubResourceReadMixin(serializers.Serializer):
    club_name = serializers.CharField(source='club.name', read_only=True)
    uploaded_by_email = serializers.SerializerMethodField()
    viewer_mode = serializers.SerializerMethodField()
    can_inline_view = serializers.SerializerMethodField()
    is_download_only = serializers.SerializerMethodField()
    opened_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()
    latest_opened_at = serializers.SerializerMethodField()

    def _can_expose_engagement_summary(self, obj):
        request = self.context.get('request')
        if request is None:
            return True

        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False

        membership = ClubMembership.objects.filter(
            user=user,
            club=obj.club,
            is_active=True,
        ).first()

        if membership is None:
            return False

        return (
            membership.can_create_content() or
            obj.engagement_visibility == ClubResource.EngagementVisibility.CLUB_VISIBLE
        )

    def get_uploaded_by_email(self, obj):
        return obj.uploaded_by.email if obj.uploaded_by else None

    def get_viewer_mode(self, obj):
        return 'inline' if obj.can_inline_view() else 'download'

    def get_can_inline_view(self, obj):
        return obj.can_inline_view()

    def get_is_download_only(self, obj):
        return obj.is_download_only()

    def get_opened_count(self, obj):
        if not self._can_expose_engagement_summary(obj):
            return None
        return obj.view_summaries.filter(opened=True).count()

    def get_completed_count(self, obj):
        if not self._can_expose_engagement_summary(obj):
            return None
        return obj.view_summaries.filter(completed=True).count()

    def get_latest_opened_at(self, obj):
        if not self._can_expose_engagement_summary(obj):
            return None

        latest_opened_at = (
            obj.view_summaries.exclude(last_opened_at__isnull=True)
            .order_by('-last_opened_at')
            .values_list('last_opened_at', flat=True)
            .first()
        )
        return latest_opened_at.isoformat() if latest_opened_at else None


class ClubResourceListSerializer(ClubResourceReadMixin, serializers.ModelSerializer):
    class Meta:
        model = ClubResource
        fields = [
            'id',
            'club',
            'club_name',
            'uploaded_by',
            'uploaded_by_email',
            'title',
            'description',
            'original_filename',
            'mime_type',
            'file_size_bytes',
            'file_kind',
            'engagement_visibility',
            'is_archived',
            'total_pages',
            'viewer_mode',
            'can_inline_view',
            'is_download_only',
            'opened_count',
            'completed_count',
            'latest_opened_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ClubResourceDetailSerializer(ClubResourceReadMixin, serializers.ModelSerializer):
    class Meta:
        model = ClubResource
        fields = [
            'id',
            'club',
            'club_name',
            'uploaded_by',
            'uploaded_by_email',
            'title',
            'description',
            'original_filename',
            'mime_type',
            'file_size_bytes',
            'file_kind',
            'engagement_visibility',
            'is_archived',
            'total_pages',
            'viewer_mode',
            'can_inline_view',
            'is_download_only',
            'opened_count',
            'completed_count',
            'latest_opened_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ClubResourceUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubResource
        fields = [
            'id',
            'title',
            'description',
            'file',
            'engagement_visibility',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        attrs = super().validate(attrs)

        uploaded_file = attrs.get('file')
        derived_metadata = _normalise_uploaded_resource_file(uploaded_file)
        attrs['_derived_resource_metadata'] = derived_metadata

        return attrs

    def create(self, validated_data):
        derived_metadata = validated_data.pop('_derived_resource_metadata')
        uploaded_file = validated_data.get('file')

        validated_data.update(derived_metadata)

        if validated_data.get('file_kind') != ClubResource.FileKind.PDF:
            validated_data['total_pages'] = None

        validated_data.setdefault('storage_backend', ClubResource.StorageBackend.LOCAL)
        validated_data.setdefault('storage_key', '')

        if cloudinary_resources_enabled():
            try:
                cloudinary_metadata = upload_club_resource_to_cloudinary(
                    uploaded_file=uploaded_file,
                    club_id=validated_data['club'].id,
                    file_kind=validated_data['file_kind'],
                    original_filename=validated_data['original_filename'],
                )
                validated_data.update(cloudinary_metadata)
            except ClubResourceStorageError:
                # Cloudinary unavailable or misconfigured — fall back to local storage
                validated_data['storage_backend'] = ClubResource.StorageBackend.LOCAL
                validated_data['storage_key'] = ''

        return ClubResource.objects.create(**validated_data)


class ClubResourceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubResource
        fields = [
            'title',
            'description',
            'engagement_visibility',
        ]


class ClubResourceArchiveSerializer(serializers.Serializer):
    is_archived = serializers.BooleanField()

    def save(self, **kwargs):
        is_archived = self.validated_data['is_archived']

        if is_archived:
            self.instance.archive()
        else:
            self.instance.unarchive()

        self.instance.refresh_from_db()
        return self.instance


class ClubResourceSignedAccessSerializer(serializers.Serializer):
    resource_id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    original_filename = serializers.CharField(read_only=True)
    mime_type = serializers.CharField(read_only=True)
    file_kind = serializers.CharField(read_only=True)
    access_mode = serializers.CharField(read_only=True)
    can_inline_view = serializers.BooleanField(read_only=True)
    is_download_only = serializers.BooleanField(read_only=True)
    access_url = serializers.URLField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)


class ClubResourceHeartbeatSerializer(serializers.Serializer):
    active_seconds_delta = serializers.IntegerField(min_value=0)
    page_reached = serializers.IntegerField(required=False, allow_null=True, min_value=0)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        resource = self.context.get('resource')
        if resource is None:
            raise serializers.ValidationError('resource context is required.')

        page_reached = attrs.get('page_reached')

        if not resource.is_pdf() and page_reached not in (None, 0):
            raise serializers.ValidationError({
                'page_reached': 'page_reached is only valid for PDF resources.',
            })

        if resource.is_pdf() and page_reached is not None and resource.total_pages:
            if page_reached > resource.total_pages:
                raise serializers.ValidationError({
                    'page_reached': 'page_reached cannot exceed the resource total_pages.',
                })

        return attrs

    def save(self, **kwargs):
        if self.instance is None:
            raise ValueError('ClubResourceHeartbeatSerializer requires an instance.')

        self.instance.update_progress(
            active_seconds_delta=self.validated_data.get('active_seconds_delta', 0),
            page_reached=self.validated_data.get('page_reached'),
        )
        self.instance.save()
        self.instance.refresh_from_db()
        return self.instance


class ClubResourceViewReadSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = ClubResourceView
        fields = [
            'id',
            'resource',
            'user',
            'user_email',
            'first_opened_at',
            'last_opened_at',
            'total_active_seconds',
            'highest_page_reached',
            'opened',
            'completed',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ClubResourceEngagementReadSerializer(serializers.ModelSerializer):
    resource_views = ClubResourceViewReadSerializer(
        source='view_summaries',
        many=True,
        read_only=True,
    )
    total_viewers = serializers.SerializerMethodField()
    opened_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()

    class Meta:
        model = ClubResource
        fields = [
            'id',
            'title',
            'engagement_visibility',
            'is_archived',
            'total_viewers',
            'opened_count',
            'completed_count',
            'resource_views',
        ]
        read_only_fields = fields

    def get_total_viewers(self, obj):
        return obj.view_summaries.count()

    def get_opened_count(self, obj):
        return obj.view_summaries.filter(opened=True).count()

    def get_completed_count(self, obj):
        return obj.view_summaries.filter(completed=True).count()
