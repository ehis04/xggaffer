from rest_framework import serializers

from ..models import ClubImportJob, ClubResource
from ..services.imports import ClubImportCommitError, commit_import_job, persist_import_preview


class ClubImportJobListSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source='club.name', read_only=True)
    uploaded_by_email = serializers.CharField(source='uploaded_by.email', read_only=True)
    source_resource_title = serializers.CharField(source='source_resource.title', read_only=True)
    source_resource_original_filename = serializers.CharField(
        source='source_resource.original_filename',
        read_only=True,
    )

    class Meta:
        model = ClubImportJob
        fields = [
            'id',
            'club',
            'club_name',
            'uploaded_by',
            'uploaded_by_email',
            'source_resource',
            'source_resource_title',
            'source_resource_original_filename',
            'import_type',
            'status',
            'row_count',
            'valid_row_count',
            'imported_row_count',
            'skipped_row_count',
            'failed_row_count',
            'warning_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ClubImportJobDetailSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source='club.name', read_only=True)
    uploaded_by_email = serializers.CharField(source='uploaded_by.email', read_only=True)
    source_resource_title = serializers.CharField(source='source_resource.title', read_only=True)
    source_resource_original_filename = serializers.CharField(
        source='source_resource.original_filename',
        read_only=True,
    )

    class Meta:
        model = ClubImportJob
        fields = [
            'id',
            'club',
            'club_name',
            'uploaded_by',
            'uploaded_by_email',
            'source_resource',
            'source_resource_title',
            'source_resource_original_filename',
            'import_type',
            'status',
            'row_count',
            'valid_row_count',
            'imported_row_count',
            'skipped_row_count',
            'failed_row_count',
            'warning_count',
            'error_summary',
            'preview_payload',
            'report_payload',
            'started_at',
            'completed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ClubImportJobCommitSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(required=True)

    def validate_confirm(self, value):
        if value is not True:
            raise serializers.ValidationError(
                'You must explicitly confirm before this import job can be committed.'
            )
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        job = self.instance
        if job is None:
            raise serializers.ValidationError('ClubImportJob instance is required.')

        if job.status != ClubImportJob.Status.PREVIEW_READY:
            raise serializers.ValidationError({
                'detail': 'Only preview_ready import jobs can be committed.'
            })

        if not job.preview_payload:
            raise serializers.ValidationError({
                'detail': 'This import job does not have a persisted preview to commit.'
            })

        if not job.preview_payload.get('can_commit', False):
            raise serializers.ValidationError({
                'detail': 'This import job does not contain any valid matched rows to commit.'
            })

        return attrs

    def save(self, **kwargs):
        confirmed_by = self.context['request'].user

        try:
            commit_import_job(
                self.instance,
                confirmed_by=confirmed_by,
            )
        except ClubImportCommitError as exc:
            raise serializers.ValidationError({
                'detail': str(exc)
            }) from exc

        self.instance.refresh_from_db()
        return self.instance


class ClubImportJobCreateSerializer(serializers.ModelSerializer):
    source_resource = serializers.PrimaryKeyRelatedField(
        queryset=ClubResource.objects.all()
    )

    class Meta:
        model = ClubImportJob
        fields = [
            'source_resource',
            'import_type',
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        club = self.context['club']
        source_resource = attrs['source_resource']

        if source_resource.club_id != club.id:
            raise serializers.ValidationError({
                'source_resource': 'source_resource must belong to the same club.'
            })

        if source_resource.file_kind not in {
            ClubResource.FileKind.CSV,
            ClubResource.FileKind.XLSX,
        }:
            raise serializers.ValidationError({
                'source_resource': 'source_resource must be a CSV or XLSX club resource.'
            })

        return attrs

    def create(self, validated_data):
        club = self.context['club']
        uploaded_by = self.context['request'].user

        job = ClubImportJob.objects.create(
            club=club,
            uploaded_by=uploaded_by,
            source_resource=validated_data['source_resource'],
            import_type=validated_data['import_type'],
        )

        persist_import_preview(job)
        job.refresh_from_db()
        return job
