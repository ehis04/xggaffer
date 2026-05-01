from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .models import User, UserRole
from .serializers import UserProfileUpdateSerializer
from .views import UserRoleView, normalise_role, role_aliases


class UserProfileUpdateSerializerTests(SimpleTestCase):
    def test_accepts_profile_edit_payload_from_legacy_frontend(self):
        serializer = UserProfileUpdateSerializer(
            data={
                "display_name": "Ada",
                "bio": "Coaching midfield rotations.",
                "gender": "",
                "visibility": "PUBLIC",
                "date_of_birth": "",
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["gender"], "NS")
        self.assertEqual(serializer.validated_data["visibility"], "PB")

    def test_accepts_current_profile_edit_payload(self):
        serializer = UserProfileUpdateSerializer(
            data={
                "gender": "NS",
                "visibility": "PR",
                "date_of_birth": None,
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["visibility"], "PR")


class UserRoleNormalisationTests(SimpleTestCase):
    def test_user_role_view_accepts_legacy_role_names(self):
        request = SimpleNamespace(data={"role": "COACH"}, query_params={})

        self.assertEqual(UserRoleView()._get_role_from_request(request), "C")

    def test_normalise_role_accepts_referee_name(self):
        self.assertEqual(normalise_role("REFEREE"), "R")

    def test_normalise_role_accepts_player_name(self):
        self.assertEqual(normalise_role("PLAYER"), "P")

    def test_role_aliases_include_legacy_and_current_values(self):
        self.assertEqual(set(role_aliases("R")), {"R", "REFEREE"})


class UserRoleViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            email="role-toggle@example.com",
            password="password123",
            username="role-toggle",
        )

    def test_delete_removes_legacy_role_value_by_current_code(self):
        UserRole.objects.create(user_profile=self.user.profile, role="REFEREE")
        request = self.factory.delete("/users/profile/role/?role=R")
        force_authenticate(request, user=self.user)

        response = UserRoleView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserRole.objects.filter(user_profile=self.user.profile).exists())

    def test_post_normalises_existing_legacy_role_value(self):
        UserRole.objects.create(user_profile=self.user.profile, role="COACH")
        request = self.factory.post("/users/profile/role/", {"role": "C"}, format="json")
        force_authenticate(request, user=self.user)

        response = UserRoleView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            UserRole.objects.filter(user_profile=self.user.profile, role="C").exists()
        )
        self.assertEqual(UserRole.objects.filter(user_profile=self.user.profile).count(), 1)
