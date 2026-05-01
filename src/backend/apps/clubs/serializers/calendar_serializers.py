from rest_framework import serializers

from ..models import ClubEvent, Fixture


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
