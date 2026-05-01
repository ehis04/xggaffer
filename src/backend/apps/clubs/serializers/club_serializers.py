from django.conf import settings
from rest_framework import serializers

from apps.players.models import ExternalProvider
from ..models import Club
from ..permissions import should_bypass_permissions


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
            "wins": enrichment.wins,
            "draws": enrichment.draws,
            "losses": enrichment.losses,
            "goals_for": enrichment.goals_for,
            "goals_against": enrichment.goals_against,
            "xg": enrichment.xg,
            "xga": enrichment.xga,
            "npxg": enrichment.npxg,
            "ppda": enrichment.ppda,
            "last_synced_at": (
                enrichment.last_synced_at.isoformat()
                if enrichment.last_synced_at else None
            ),
        }


class ClubSerializer(ClubUnderstatSummaryMixin, serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    player_count = serializers.IntegerField(read_only=True)
    fan_count = serializers.IntegerField(read_only=True)
    is_followed = serializers.SerializerMethodField()
    creator_username = serializers.CharField(source="creator.email", read_only=True)
    trashed_by = serializers.IntegerField(source="trashed_by_id", read_only=True)

    def get_is_followed(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return obj.fans.filter(user=user).exists()

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
            "fan_count",
            "is_followed",
            "latest_understat_summary",
            "is_trashed",
            "trashed_at",
            "trash_expires_at",
            "trashed_by",
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
    fan_count = serializers.IntegerField(read_only=True)
    is_followed = serializers.SerializerMethodField()
    creator_username = serializers.CharField(source="creator.email", read_only=True)

    def get_is_followed(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return obj.fans.filter(user=user).exists()

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
            "fan_count",
            "is_followed",
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
            "fan_count",
            "is_followed",
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

        if should_bypass_permissions():
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


class ClubDuplicateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    include_players = serializers.BooleanField(default=True)
    visibility = serializers.ChoiceField(
        choices=Club.Visibility.choices,
        default=Club.Visibility.PRIVATE,
    )


class ClubTrashActionSerializer(serializers.Serializer):
    pass


class ClubListSerializer(ClubUnderstatSummaryMixin, serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    player_count = serializers.IntegerField(read_only=True)
    fan_count = serializers.IntegerField(read_only=True)
    is_followed = serializers.SerializerMethodField()
    creator_username = serializers.CharField(source="creator.email", read_only=True)
    trashed_by = serializers.IntegerField(source="trashed_by_id", read_only=True)

    def get_is_followed(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return obj.fans.filter(user=user).exists()

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
            "fan_count",
            "is_followed",
            "latest_understat_summary",
            "is_trashed",
            "trashed_at",
            "trash_expires_at",
            "trashed_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["creator", "created_at", "updated_at"]


class TrashListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    section = serializers.ChoiceField(choices=['clubs', 'teamsheets', 'tactics'])
    title = serializers.CharField()
    secondary_text = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    club_id = serializers.IntegerField(allow_null=True)
    club_name = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    trashed_at = serializers.DateTimeField(allow_null=True)
    trash_expires_at = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)
    route_path = serializers.CharField()
