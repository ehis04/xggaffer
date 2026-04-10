import re

from django.conf import settings
from rest_framework import serializers
from .storage import (
    ClubResourceStorageError,
    cloudinary_resources_enabled,
    upload_club_resource_to_cloudinary,
)
from apps.players.models import ExternalProvider, Player
from common.constants import Position, PreferredFoot
from .models import (
    Club,
    ClubInvitation,
    ClubJoinRequest,
    ClubMembership,
    ClubPlayer,
    ClubEvent,
    Fixture,
    ClubResource,
    ClubResourceView,
    ClubImportJob,
)
from .services.imports import ClubImportCommitError, commit_import_job, persist_import_preview

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

def _image_url(file_field):
    if not file_field:
        return None

    try:
        return file_field.url
    except Exception:
        return None


class ClubUnderstatSummaryMixin(serializers.Serializer):
    latest_understat_summary = serializers.SerializerMethodField()

    def _get_latest_understat_enrichment(self, obj):
        prefetched = getattr(obj, "prefetched_understat_enrichments", None)
        if prefetched is not None:
            return prefetched[0] if prefetched else None

        return (
            obj.season_enrichments.filter(provider=ExternalProvider.UNDERSTAT)
            .order_by("-season_label", "-updated_at", "-id")
            .first()
        )

    def get_latest_understat_summary(self, obj):
        enrichment = self._get_latest_understat_enrichment(obj)
        if not enrichment:
            return None

        return {
            "provider": enrichment.provider,
            "season_label": enrichment.season_label,
            "competition_code": enrichment.competition_code,
            "competition_name": enrichment.competition_name,
            "matches_played": enrichment.matches_played,
            "xg": enrichment.xg,
            "xga": enrichment.xga,
            "npxg": enrichment.npxg,
            "last_synced_at": (
                enrichment.last_synced_at.isoformat()
                if enrichment.last_synced_at else None
            ),
        }


class ClubSerializer(ClubUnderstatSummaryMixin, serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    player_count = serializers.IntegerField(read_only=True)
    creator_username = serializers.CharField(source="creator.email", read_only=True)

    class Meta:
        model = Club
        fields = [
            "id",
            "name",
            "description",
            "badge",
            "creator",
            "creator_username",
            "visibility",
            "club_type",
            "fictional_basis",
            "source_real_club_name",
            "directory_visibility",
            "join_policy",
            "join_code",
            "verification_status",
            "city",
            "country",
            "stadium",
            "division",
            "achievements",
            "member_count",
            "player_count",
            "latest_understat_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "creator",
            "creator_username",
            "join_code",
            "created_at",
            "updated_at",
        ]


class ClubWriteSerializer(ClubUnderstatSummaryMixin, serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    player_count = serializers.IntegerField(read_only=True)
    creator_username = serializers.CharField(source="creator.email", read_only=True)

    class Meta:
        model = Club
        fields = [
            "id",
            "name",
            "description",
            "badge",
            "creator",
            "creator_username",
            "visibility",
            "club_type",
            "fictional_basis",
            "source_real_club_name",
            "directory_visibility",
            "join_policy",
            "join_code",
            "verification_status",
            "verification_contact_name",
            "verification_contact_role",
            "verification_contact_email",
            "verification_evidence_text",
            "verification_evidence_url",
            "city",
            "country",
            "stadium",
            "division",
            "achievements",
            "member_count",
            "player_count",
            "latest_understat_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "creator",
            "creator_username",
            "join_code",
            "verification_status",
            "member_count",
            "player_count",
            "latest_understat_summary",
            "created_at",
            "updated_at",
        ]

    def _get_request_user(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            return user
        return None

    def _can_submit_system_professional(self):
        user = self._get_request_user()

        if getattr(settings, "BYPASS_PERMISSIONS", False):
            return True

        return bool(user and (user.is_staff or user.is_superuser))

    def _get_effective_value(self, attrs, field_name):
        if field_name in attrs:
            return attrs[field_name]
        if self.instance is not None:
            return getattr(self.instance, field_name)
        return None

    def _normalise_choice_blanks(self, attrs):
        choice_fields = [
            "club_type",
            "fictional_basis",
            "directory_visibility",
            "join_policy",
        ]

        for field_name in choice_fields:
            if attrs.get(field_name) == "":
                attrs[field_name] = None

        return attrs

    def _apply_managed_defaults(self, attrs):
        current_club_type = getattr(self.instance, "club_type", None)
        current_verification_status = getattr(self.instance, "verification_status", None)

        if self.instance is None and not attrs.get("club_type"):
            attrs["club_type"] = Club.ClubType.USER_FICTIONAL

        effective_club_type = self._get_effective_value(attrs, "club_type")

        if effective_club_type == Club.ClubType.USER_FICTIONAL:
            if not self._get_effective_value(attrs, "fictional_basis"):
                attrs["fictional_basis"] = Club.FictionalBasis.ORIGINAL

        if effective_club_type != Club.ClubType.USER_FICTIONAL:
            attrs["fictional_basis"] = None

        if not self._get_effective_value(attrs, "directory_visibility"):
            attrs["directory_visibility"] = Club.DirectoryVisibility.LISTED

        if effective_club_type == Club.ClubType.SYSTEM_PROFESSIONAL:
            attrs["join_policy"] = Club.JoinPolicy.SYSTEM_MANAGED
            attrs["verification_status"] = Club.VerificationStatus.NOT_REQUIRED
            return attrs

        if not self._get_effective_value(attrs, "join_policy"):
            attrs["join_policy"] = Club.JoinPolicy.APPROVAL_REQUIRED

        if effective_club_type == Club.ClubType.USER_REAL_NON_PRO:
            if current_club_type != Club.ClubType.USER_REAL_NON_PRO:
                attrs["verification_status"] = Club.VerificationStatus.PENDING
            elif not current_verification_status:
                attrs["verification_status"] = Club.VerificationStatus.PENDING
            return attrs

        if effective_club_type == Club.ClubType.USER_FICTIONAL:
            attrs["verification_status"] = Club.VerificationStatus.NOT_REQUIRED

        return attrs

    def _build_candidate_instance(self, attrs):
        if self.instance is not None:
            candidate = Club()
            for field in self.instance._meta.concrete_fields:
                setattr(candidate, field.name, getattr(self.instance, field.name))
            candidate._state.adding = False
            candidate._state.db = self.instance._state.db
        else:
            candidate = Club()
            request_user = self._get_request_user()
            if request_user is not None:
                candidate.creator = request_user

        for field_name, value in attrs.items():
            setattr(candidate, field_name, value)

        candidate.apply_taxonomy_defaults()

        if candidate.is_hidden_from_directory() and not candidate.join_code:
            candidate.generate_join_code(commit=False)

        return candidate

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs = self._normalise_choice_blanks(attrs)
        attrs = self._apply_managed_defaults(attrs)

        effective_club_type = self._get_effective_value(attrs, "club_type")

        if (
            effective_club_type == Club.ClubType.SYSTEM_PROFESSIONAL
            and not self._can_submit_system_professional()
        ):
            raise serializers.ValidationError({
                "club_type": (
                    "system_professional clubs are system-managed and cannot be "
                    "submitted through ordinary user flows."
                )
            })

        candidate = self._build_candidate_instance(attrs)
        candidate.full_clean()

        return attrs


class ClubPlayerCanonicalLinkStateMixin(serializers.Serializer):
    is_linked_to_player = serializers.SerializerMethodField()
    canonical_player_id = serializers.SerializerMethodField()
    canonical_display_name = serializers.SerializerMethodField()
    canonical_primary_position = serializers.SerializerMethodField()

    def get_is_linked_to_player(self, obj):
        return obj.is_linked_to_player

    def get_canonical_player_id(self, obj):
        return obj.player_id

    def get_canonical_display_name(self, obj):
        if not obj.player_id:
            return None
        return obj.player.display_name or obj.player.full_name

    def get_canonical_primary_position(self, obj):
        if not obj.player_id:
            return None
        return obj.player.primary_position or ""


class ClubPlayerProviderStatusMixin(serializers.Serializer):
    player_id = serializers.SerializerMethodField()
    has_provider_identity = serializers.SerializerMethodField()
    provider_sources = serializers.SerializerMethodField()
    last_synced_at = serializers.SerializerMethodField()

    def get_player_id(self, obj):
        return obj.player_id

    def get_has_provider_identity(self, obj):
        if not obj.player_id:
            return False
        return obj.player.external_identities.exists()

    def get_provider_sources(self, obj):
        if not obj.player_id:
            return []

        return list(
            obj.player.external_identities.order_by("provider")
            .values_list("provider", flat=True)
            .distinct()
        )

    def get_last_synced_at(self, obj):
        if not obj.player_id:
            return None

        last_synced_at = (
            obj.player.external_identities.exclude(last_synced_at__isnull=True)
            .order_by("-last_synced_at")
            .values_list("last_synced_at", flat=True)
            .first()
        )

        return last_synced_at.isoformat() if last_synced_at else None


class ClubMembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.email", read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = ClubMembership
        fields = [
            "id",
            "user",
            "username",
            "club",
            "club_name",
            "role",
            "is_active",
            "invited_by",
            "joined_at",
            "updated_at",
        ]
        read_only_fields = ["joined_at", "updated_at"]


class ClubJoinRequestSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    reviewed_by_email = serializers.CharField(source="reviewed_by.email", read_only=True)
    selected_club_player_name = serializers.CharField(
        source="selected_club_player.full_name",
        read_only=True,
    )

    class Meta:
        model = ClubJoinRequest
        fields = [
            "id",
            "club",
            "club_name",
            "user",
            "user_email",
            "requested_role",
            "message",
            "status",
            "reviewed_by",
            "reviewed_by_email",
            "reviewed_at",
            "review_note",
            "selected_club_player",
            "selected_club_player_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "club",
            "club_name",
            "user",
            "user_email",
            "status",
            "reviewed_by",
            "reviewed_by_email",
            "reviewed_at",
            "review_note",
            "created_at",
            "updated_at",
        ]


class ClubJoinRequestCreateSerializer(serializers.ModelSerializer):
    requested_role = serializers.ChoiceField(
        choices=ClubMembership.Role.choices,
        default=ClubMembership.Role.PLAYER,
    )

    class Meta:
        model = ClubJoinRequest
        fields = [
            "requested_role",
            "message",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        request = self.context["request"]
        club = self.context["club"]

        candidate = ClubJoinRequest(
            club=club,
            user=request.user,
            requested_role=attrs.get("requested_role", ClubMembership.Role.PLAYER),
            message=attrs.get("message", ""),
        )
        candidate.full_clean()

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        club = self.context["club"]

        return ClubJoinRequest.objects.create(
            club=club,
            user=request.user,
            **validated_data,
        )


class ClubJoinRequestApproveSerializer(serializers.Serializer):
    review_note = serializers.CharField(required=False, allow_blank=True)
    selected_club_player = serializers.PrimaryKeyRelatedField(
        queryset=ClubPlayer.objects.all(),
        required=False,
        allow_null=True,
    )

    def validate_selected_club_player(self, value):
        if value is None:
            return value

        join_request = self.instance
        if join_request is None:
            raise serializers.ValidationError("Join request context is required.")

        if value.club_id != join_request.club_id:
            raise serializers.ValidationError("Selected ClubPlayer must belong to the same club.")

        if value.user_id is not None:
            raise serializers.ValidationError("Selected ClubPlayer is already claimed.")

        return value

    def save(self, **kwargs):
        review_note = self.validated_data.get("review_note", "")
        selected_club_player = self.validated_data.get("selected_club_player")
        reviewer = self.context["request"].user

        self.instance.mark_approved(
            reviewed_by=reviewer,
            review_note=review_note,
            selected_club_player=selected_club_player,
        )
        self.instance.refresh_from_db()
        return self.instance


class ClubJoinRequestRejectSerializer(serializers.Serializer):
    review_note = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        reviewer = self.context["request"].user
        review_note = self.validated_data.get("review_note", "")

        self.instance.mark_rejected(
            reviewed_by=reviewer,
            review_note=review_note,
        )
        self.instance.refresh_from_db()
        return self.instance


class ClubJoinRequestWithdrawSerializer(serializers.Serializer):
    def save(self, **kwargs):
        self.instance.mark_withdrawn()
        self.instance.refresh_from_db()
        return self.instance


class ClubInvitationSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    invited_user_email = serializers.CharField(source="invited_user.email", read_only=True)
    invited_by_email = serializers.CharField(source="invited_by.email", read_only=True)

    class Meta:
        model = ClubInvitation
        fields = [
            "id",
            "club",
            "club_name",
            "invited_user",
            "invited_user_email",
            "invited_by",
            "invited_by_email",
            "invited_role",
            "note",
            "status",
            "responded_at",
            "response_note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "club",
            "club_name",
            "invited_by",
            "invited_by_email",
            "status",
            "responded_at",
            "response_note",
            "created_at",
            "updated_at",
        ]


class ClubInvitationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubInvitation
        fields = [
            "invited_user",
            "invited_role",
            "note",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        club = self.context["club"]
        inviter = self.context["request"].user

        candidate = ClubInvitation(
            club=club,
            invited_user=attrs["invited_user"],
            invited_by=inviter,
            invited_role=attrs["invited_role"],
            note=attrs.get("note", ""),
        )
        candidate.full_clean()

        return attrs

    def create(self, validated_data):
        club = self.context["club"]
        inviter = self.context["request"].user

        return ClubInvitation.objects.create(
            club=club,
            invited_by=inviter,
            **validated_data,
        )


class ClubInvitationAcceptSerializer(serializers.Serializer):
    response_note = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        response_note = self.validated_data.get("response_note", "")
        self.instance.mark_accepted(response_note=response_note)
        self.instance.refresh_from_db()
        return self.instance


class ClubInvitationDeclineSerializer(serializers.Serializer):
    response_note = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        response_note = self.validated_data.get("response_note", "")
        self.instance.mark_declined(response_note=response_note)
        self.instance.refresh_from_db()
        return self.instance


class ClubInvitationRevokeSerializer(serializers.Serializer):
    response_note = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        response_note = self.validated_data.get("response_note", "")
        self.instance.mark_revoked(response_note=response_note)
        self.instance.refresh_from_db()
        return self.instance


class ClubPlayerIdentityReadMixin(serializers.Serializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    primary_position = serializers.SerializerMethodField()
    secondary_positions = serializers.SerializerMethodField()
    preferred_foot = serializers.SerializerMethodField()
    date_of_birth = serializers.SerializerMethodField()
    height_cm = serializers.SerializerMethodField()
    nationality = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()

    def _identity(self, obj):
        return obj.get_display_player_identity()

    def get_first_name(self, obj):
        return self._identity(obj)["first_name"]

    def get_last_name(self, obj):
        return self._identity(obj)["last_name"]

    def get_full_name(self, obj):
        return self._identity(obj)["full_name"]

    def get_display_name(self, obj):
        return self._identity(obj)["display_name"]

    def get_primary_position(self, obj):
        return self._identity(obj)["primary_position"]

    def get_secondary_positions(self, obj):
        return self._identity(obj)["secondary_positions"]

    def get_preferred_foot(self, obj):
        return self._identity(obj)["preferred_foot"]

    def get_date_of_birth(self, obj):
        return self._identity(obj)["date_of_birth"]

    def get_height_cm(self, obj):
        return self._identity(obj)["height_cm"]

    def get_nationality(self, obj):
        return self._identity(obj)["nationality"]

    def get_photo(self, obj):
        return _image_url(self._identity(obj)["photo"])


class BaseClubPlayerWriteSerializer(serializers.ModelSerializer):
    canonical_player_id = serializers.PrimaryKeyRelatedField(
        source="player",
        queryset=Player.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    display_name = serializers.CharField(required=False, allow_blank=True)
    primary_position = serializers.ChoiceField(
        choices=Position.choices,
        required=False,
        allow_blank=True,
    )
    secondary_positions = serializers.ListField(
        child=serializers.ChoiceField(choices=Position.choices),
        required=False,
    )
    preferred_foot = serializers.ChoiceField(
        choices=PreferredFoot.choices,
        required=False,
        allow_blank=True,
    )
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    height_cm = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    photo = serializers.ImageField(required=False, allow_null=True)
    squad_number = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    class Meta:
        model = ClubPlayer
        fields = [
            "id",
            "club",
            "player",
            "user",
            "canonical_player_id",
            "first_name",
            "last_name",
            "display_name",
            "squad_number",
            "primary_position",
            "secondary_positions",
            "preferred_foot",
            "date_of_birth",
            "height_cm",
            "photo",
            "is_public",
            "is_active",
        ]
        read_only_fields = ["id", "club", "player", "user"]

    def _get_club(self):
        return self.context.get("club") or getattr(self.instance, "club", None)

    def _effective_value(self, attrs, field_name, default=None):
        if field_name in attrs:
            return attrs[field_name]
        if self.instance is not None:
            return getattr(self.instance, field_name, default)
        return default

    def _normalise_identity_from_canonical(self, attrs):
        canonical_player = attrs.get("player")
        if canonical_player is None:
            return attrs

        if not attrs.get("first_name"):
            attrs["first_name"] = canonical_player.first_name
        if not attrs.get("last_name"):
            attrs["last_name"] = canonical_player.last_name
        if not attrs.get("display_name"):
            attrs["display_name"] = canonical_player.display_name or ""
        if not attrs.get("primary_position"):
            attrs["primary_position"] = canonical_player.primary_position or ""
        if "secondary_positions" not in attrs:
            attrs["secondary_positions"] = list(canonical_player.secondary_positions or [])
        if not attrs.get("preferred_foot"):
            attrs["preferred_foot"] = canonical_player.preferred_foot or ""
        if attrs.get("date_of_birth") is None:
            attrs["date_of_birth"] = canonical_player.date_of_birth
        if attrs.get("height_cm") is None:
            attrs["height_cm"] = canonical_player.height_cm

        return attrs

    def _is_generic_name(self, first_name, last_name, club, primary_position, squad_number):
        if not first_name and not last_name:
            return True

        club_name = club.name.lower() if club else ""
        full_name = f"{first_name} {last_name}".lower().strip()
        position_text = (primary_position or "").lower()

        generic_patterns = [
            rf"^{re.escape(club_name)}.*{re.escape(position_text)}" if club_name and position_text else None,
            rf"^{re.escape(position_text)}.*#?\d+" if position_text else None,
            r"^player\s*#?\d+",
            rf"^{re.escape(club_name)}.*#?\d+" if club_name else None,
        ]

        for pattern in generic_patterns:
            if pattern and re.search(pattern, full_name):
                return True

        if squad_number and f"#{squad_number}" in full_name:
            return True

        return False

    def _validate_public_name_rules(self, attrs):
        club = self._get_club()
        first_name = (self._effective_value(attrs, "first_name", "") or "").strip()
        last_name = (self._effective_value(attrs, "last_name", "") or "").strip()
        primary_position = self._effective_value(attrs, "primary_position", "") or ""
        squad_number = self._effective_value(attrs, "squad_number", None)
        is_public = bool(self._effective_value(attrs, "is_public", False))

        if not is_public or not (first_name or last_name):
            return

        if club and not self._is_generic_name(
            first_name=first_name,
            last_name=last_name,
            club=club,
            primary_position=primary_position,
            squad_number=squad_number,
        ):
            raise serializers.ValidationError({
                "is_public": (
                    "Public profiles cannot use real names. "
                    "Use a generic format like 'Club Name GK #1'."
                )
            })

    def _apply_local_field_mapping(self, validated_data):
        secondary_positions = validated_data.pop("secondary_positions", None)
        if secondary_positions is not None:
            validated_data["secondary_position"] = secondary_positions[0] if secondary_positions else ""
        return validated_data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs = self._normalise_identity_from_canonical(attrs)

        first_name = (attrs.get("first_name") or "").strip()
        last_name = (attrs.get("last_name") or "").strip()

        if self.instance is None:
            if not first_name:
                raise serializers.ValidationError({"first_name": "First name is required."})
            if not last_name:
                raise serializers.ValidationError({"last_name": "Last name is required."})

        canonical_player = attrs.get("player")
        if canonical_player is not None:
            candidate = self.instance or ClubPlayer(club=self._get_club())
            candidate.can_link_to_player(canonical_player)

        self._validate_public_name_rules(attrs)
        return attrs

    def create(self, validated_data):
        validated_data = self._apply_local_field_mapping(validated_data)

        is_public = validated_data.get("is_public", False)
        if is_public and not validated_data.get("display_name"):
            club = self._get_club()
            primary_position = validated_data.get("primary_position") or "Player"
            squad_number = validated_data.get("squad_number")
            club_name = club.name if club else "Team"
            number_text = f" #{squad_number}" if squad_number else ""
            validated_data["display_name"] = f"{club_name} {primary_position}{number_text}"

        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._apply_local_field_mapping(validated_data)
        return super().update(instance, validated_data)


class ClubPlayerSerializer(
    ClubPlayerIdentityReadMixin,
    ClubPlayerCanonicalLinkStateMixin,
    ClubPlayerProviderStatusMixin,
    serializers.ModelSerializer,
):
    is_claimed = serializers.BooleanField(read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = ClubPlayer
        fields = [
            "id",
            "club",
            "club_name",
            "player",
            "user",
            "first_name",
            "last_name",
            "full_name",
            "display_name",
            "squad_number",
            "primary_position",
            "secondary_positions",
            "preferred_foot",
            "date_of_birth",
            "height_cm",
            "nationality",
            "photo",
            "is_active",
            "is_claimed",
            "is_public",
            "created_at",
            "updated_at",
            "player_id",
            "is_linked_to_player",
            "canonical_player_id",
            "canonical_display_name",
            "canonical_primary_position",
            "has_provider_identity",
            "provider_sources",
            "last_synced_at",
        ]
        read_only_fields = [
            "player",
            "user",
            "is_claimed",
            "created_at",
            "updated_at",
            "player_id",
            "is_linked_to_player",
            "canonical_player_id",
            "canonical_display_name",
            "canonical_primary_position",
            "has_provider_identity",
            "provider_sources",
            "last_synced_at",
        ]


class ClubPlayerListSerializer(
    ClubPlayerIdentityReadMixin,
    ClubPlayerCanonicalLinkStateMixin,
    ClubPlayerProviderStatusMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = ClubPlayer
        fields = [
            "id",
            "player",
            "first_name",
            "last_name",
            "full_name",
            "display_name",
            "squad_number",
            "primary_position",
            "secondary_positions",
            "preferred_foot",
            "date_of_birth",
            "height_cm",
            "nationality",
            "photo",
            "is_active",
            "is_public",
            "player_id",
            "is_linked_to_player",
            "canonical_player_id",
            "canonical_display_name",
            "canonical_primary_position",
            "has_provider_identity",
            "provider_sources",
            "last_synced_at",
        ]
        read_only_fields = fields


class ClubPlayerCreateSerializer(BaseClubPlayerWriteSerializer):
    pass


class ClubPlayerUpdateSerializer(BaseClubPlayerWriteSerializer):
    def validate(self, attrs):
        if "player" in attrs:
            requested_player = attrs.get("player")
            requested_player_id = requested_player.id if requested_player else None

            if requested_player_id != self.instance.player_id:
                raise serializers.ValidationError({
                    "canonical_player_id": (
                        "Use explicit link, unlink, or relink actions to change canonical alignment."
                    )
                })

        return super().validate(attrs)


class ClubPlayerLinkSerializer(serializers.Serializer):
    canonical_player_id = serializers.PrimaryKeyRelatedField(
        source="player",
        queryset=Player.objects.all(),
    )

    def validate(self, attrs):
        self.instance.can_link_to_player(attrs["player"])
        return attrs

    def save(self, **kwargs):
        self.instance.link_to_player(self.validated_data["player"])
        self.instance.refresh_from_db()
        return self.instance


class ClubPlayerUnlinkSerializer(serializers.Serializer):
    def save(self, **kwargs):
        self.instance.unlink_player()
        self.instance.refresh_from_db()
        return self.instance


class ClubPlayerRelinkSerializer(serializers.Serializer):
    canonical_player_id = serializers.PrimaryKeyRelatedField(
        source="player",
        queryset=Player.objects.all(),
    )

    def validate(self, attrs):
        self.instance.can_link_to_player(attrs["player"], allow_relink=True)
        return attrs

    def save(self, **kwargs):
        self.instance.relink_player(self.validated_data["player"])
        self.instance.refresh_from_db()
        return self.instance


class AvailablePlayerSerializer(
    ClubPlayerIdentityReadMixin,
    ClubPlayerProviderStatusMixin,
    serializers.ModelSerializer,
):
    club = serializers.IntegerField(source="club_id", read_only=True)
    source_type = serializers.SerializerMethodField()

    class Meta:
        model = ClubPlayer
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "display_name",
            "squad_number",
            "primary_position",
            "photo",
            "club",
            "is_public",
            "source_type",
            "player_id",
            "has_provider_identity",
            "provider_sources",
            "last_synced_at",
        ]

    def get_source_type(self, obj):
        club_id = self.context.get("club_id")
        if club_id and obj.club_id == club_id:
            return "club_member"
        if obj.is_public:
            return "public"
        return "unknown"


class ClubDuplicateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    include_players = serializers.BooleanField(default=True)
    visibility = serializers.ChoiceField(
        choices=Club.Visibility.choices,
        default=Club.Visibility.PRIVATE,
    )


class ClubListSerializer(ClubUnderstatSummaryMixin, serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    player_count = serializers.IntegerField(read_only=True)
    creator_username = serializers.CharField(source="creator.email", read_only=True)

    class Meta:
        model = Club
        fields = [
            "id",
            "name",
            "description",
            "badge",
            "creator",
            "creator_username",
            "visibility",
            "city",
            "country",
            "stadium",
            "division",
            "achievements",
            "member_count",
            "player_count",
            "latest_understat_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["creator", "created_at", "updated_at"]


class SchedulingStateReadMixin(serializers.Serializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)
    is_user_editable = serializers.SerializerMethodField()
    is_system_managed_item = serializers.SerializerMethodField()
    is_future_item = serializers.SerializerMethodField()
    calendar_label = serializers.SerializerMethodField()

    def get_is_user_editable(self, obj):
        return obj.is_user_editable()

    def get_is_system_managed_item(self, obj):
        return obj.is_system_managed_item()

    def get_is_future_item(self, obj):
        return obj.is_future_item()

    def get_calendar_label(self, obj):
        return obj.get_calendar_label()


class BaseClubSchedulingWriteSerializer(serializers.ModelSerializer):
    def _get_context_club(self):
        return self.context.get("club") or getattr(self.instance, "club", None)

    def _get_request_user(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            return user
        return None

    def _build_candidate_instance(self, attrs):
        if self.instance is not None:
            candidate = self.Meta.model()
            for field in self.instance._meta.concrete_fields:
                setattr(candidate, field.name, getattr(self.instance, field.name))
            candidate._state.adding = False
            candidate._state.db = self.instance._state.db
        else:
            candidate = self.Meta.model()
            club = self._get_context_club()
            if club is not None:
                candidate.club = club

            request_user = self._get_request_user()
            if request_user is not None and hasattr(candidate, "created_by"):
                candidate.created_by = request_user

        for field_name, value in attrs.items():
            setattr(candidate, field_name, value)

        return candidate

    def validate(self, attrs):
        attrs = super().validate(attrs)

        club = self._get_context_club()
        if self.instance is None and club is None:
            raise serializers.ValidationError({
                "club": "Club context is required for scheduling writes."
            })

        if self.instance is not None and not self.instance.is_user_editable():
            raise serializers.ValidationError({
                "non_field_errors": [
                    "This scheduling item is system-managed and cannot be edited through ordinary user flows."
                ]
            })

        candidate = self._build_candidate_instance(attrs)
        candidate.full_clean()

        return attrs


class ClubEventSerializer(SchedulingStateReadMixin, serializers.ModelSerializer):
    event_type_display = serializers.CharField(
        source="get_event_type_display",
        read_only=True,
    )
    source_type_display = serializers.CharField(
        source="get_source_type_display",
        read_only=True,
    )

    class Meta:
        model = ClubEvent
        fields = [
            "id",
            "club",
            "club_name",
            "title",
            "event_type",
            "event_type_display",
            "description",
            "start_datetime",
            "end_datetime",
            "is_all_day",
            "location",
            "is_mandatory",
            "source_type",
            "source_type_display",
            "created_by",
            "created_by_email",
            "is_user_editable",
            "is_system_managed_item",
            "is_future_item",
            "calendar_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "club",
            "club_name",
            "source_type",
            "source_type_display",
            "created_by",
            "created_by_email",
            "is_user_editable",
            "is_system_managed_item",
            "is_future_item",
            "calendar_label",
            "created_at",
            "updated_at",
        ]


class ClubEventWriteSerializer(BaseClubSchedulingWriteSerializer):
    class Meta:
        model = ClubEvent
        fields = [
            "id",
            "title",
            "event_type",
            "description",
            "start_datetime",
            "end_datetime",
            "is_all_day",
            "location",
            "is_mandatory",
        ]
        read_only_fields = ["id"]


class FixtureSerializer(SchedulingStateReadMixin, serializers.ModelSerializer):
    venue_display = serializers.CharField(
        source="get_venue_display",
        read_only=True,
    )
    fixture_status_display = serializers.CharField(
        source="get_fixture_status_display",
        read_only=True,
    )
    source_type_display = serializers.CharField(
        source="get_source_type_display",
        read_only=True,
    )

    class Meta:
        model = Fixture
        fields = [
            "id",
            "club",
            "club_name",
            "opponent_name",
            "venue",
            "venue_display",
            "competition",
            "match_datetime",
            "location",
            "fixture_status",
            "fixture_status_display",
            "source_type",
            "source_type_display",
            "external_fixture_id",
            "created_by",
            "created_by_email",
            "is_user_editable",
            "is_system_managed_item",
            "is_future_item",
            "calendar_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "club",
            "club_name",
            "source_type",
            "source_type_display",
            "external_fixture_id",
            "created_by",
            "created_by_email",
            "is_user_editable",
            "is_system_managed_item",
            "is_future_item",
            "calendar_label",
            "created_at",
            "updated_at",
        ]


class FixtureWriteSerializer(BaseClubSchedulingWriteSerializer):
    class Meta:
        model = Fixture
        fields = [
            "id",
            "opponent_name",
            "venue",
            "competition",
            "match_datetime",
            "location",
            "fixture_status",
        ]
        read_only_fields = ["id"]

class ClubCalendarFeedItemSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=['event', 'fixture'])
    sort_datetime = serializers.DateTimeField()
    calendar_label = serializers.CharField()
    event = serializers.SerializerMethodField()
    fixture = serializers.SerializerMethodField()

    def get_event(self, obj):
        if obj['item_type'] != 'event':
            return None
        return ClubEventSerializer(
            obj['event'],
            context=self.context,
        ).data

    def get_fixture(self, obj):
        if obj['item_type'] != 'fixture':
            return None
        return FixtureSerializer(
            obj['fixture'],
            context=self.context,
        ).data

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