from django.contrib.auth import get_user_model
from rest_framework import serializers

from ..models import Club, ClubInvitation, ClubJoinRequest, ClubMembership, ClubPlayer


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


class ClubInvitationCreateSerializer(serializers.Serializer):
    invited_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(),
        required=False,
    )
    invited_email = serializers.EmailField(required=False)
    invited_role = serializers.ChoiceField(choices=["admin", "coach", "player", "viewer"])
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_invited_email(self, value):
        User = get_user_model()
        try:
            return User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with that email address.")

    def validate(self, attrs):
        club = self.context["club"]
        inviter = self.context["request"].user

        invited_user = attrs.get("invited_user")
        if invited_user is None:
            invited_user = attrs.get("invited_email")

        if invited_user is None:
            raise serializers.ValidationError({
                "invited_user": "Provide invited_user or invited_email.",
            })

        attrs["invited_user"] = invited_user

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
            invited_user=validated_data["invited_user"],
            invited_role=validated_data["invited_role"],
            note=validated_data.get("note", ""),
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
