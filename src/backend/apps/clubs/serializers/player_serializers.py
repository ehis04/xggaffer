import re

from rest_framework import serializers

from apps.players.models import Player
from common.constants import Position, PreferredFoot
from ..models import ClubPlayer, ClubPlayerInjury
from .club_serializers import _image_url


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


class ClubPlayerWithAvailabilitySerializer(
    ClubPlayerIdentityReadMixin,
    ClubPlayerCanonicalLinkStateMixin,
    ClubPlayerProviderStatusMixin,
    serializers.ModelSerializer,
):
    is_claimed = serializers.BooleanField(read_only=True)
    club_name = serializers.CharField(source='club.name', read_only=True)
    availability_status = serializers.SerializerMethodField()
    current_injury = serializers.SerializerMethodField()
    fitness_score = serializers.SerializerMethodField()

    class Meta:
        model = ClubPlayer
        fields = [
            'id',
            'club',
            'club_name',
            'player',
            'user',
            'first_name',
            'last_name',
            'display_name',
            'squad_number',
            'primary_position',
            'secondary_positions',
            'preferred_foot',
            'date_of_birth',
            'height_cm',
            'photo',
            'is_public',
            'is_active',
            'is_claimed',
            'availability_status',
            'current_injury',
            'fitness_score',
            'is_linked_to_player',
            'canonical_player_id',
            'canonical_display_name',
            'canonical_primary_position',
            'player_id',
            'has_provider_identity',
            'provider_sources',
            'last_synced_at',
            'created_at',
        ]
        read_only_fields = ['id', 'club', 'player', 'user']

    def get_availability_status(self, obj):
        injury = obj.injuries.filter(is_current=True).first()
        if injury:
            return injury.availability_status
        return ClubPlayerInjury.AvailabilityStatus.AVAILABLE

    def get_current_injury(self, obj):
        from .player_tracking_serializers import ClubPlayerInjurySerializer
        injury = obj.injuries.filter(is_current=True).select_related('recorded_by').first()
        if injury:
            return ClubPlayerInjurySerializer(injury).data
        return None

    def get_fitness_score(self, obj):
        injury = obj.injuries.filter(is_current=True).first()
        if injury:
            if injury.availability_status in (
                ClubPlayerInjury.AvailabilityStatus.INJURED,
                ClubPlayerInjury.AvailabilityStatus.SUSPENDED,
            ):
                return 0
            if injury.availability_status == ClubPlayerInjury.AvailabilityStatus.IN_DOUBT:
                return 45

        player = obj.player
        if player is None:
            return 85

        enrichments = getattr(player, 'prefetched_season_enrichments', None)
        if enrichments is None:
            enrichments = list(
                player.season_enrichments.order_by('-season_label', '-id')[:1]
            )

        latest = enrichments[0] if enrichments else None
        if latest is None or latest.matches_played == 0:
            return 85

        ratio = latest.minutes_played / (latest.matches_played * 90)
        if ratio >= 0.8:
            return 92
        if ratio >= 0.6:
            return 85
        if ratio >= 0.4:
            return 74
        if ratio >= 0.2:
            return 63
        return 85
