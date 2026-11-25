from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Follow, FollowRequest, User, UserRole, Visibility
from .serializers import UserProfileUpdateSerializer
from .views import UserRoleView, normalise_role, role_aliases


class AccountIsolationTests(TestCase):
    def setUp(self):
        self.auth_url = "/api/users/auth"
        self.first = User.objects.create_user(
            email="first@example.com", username="first", password="example-password", email_verified=True,
        )
        self.second = User.objects.create_user(
            email="second@example.com", username="second", password="example-password",
        )

    def test_verifying_link_for_second_account_keeps_first_session(self):
        self.client.post(self.auth_url + "/login/", {"email": self.first.email, "password": "example-password"})
        token = self.second.generate_verification_token()
        response = self.client.post(self.auth_url + "/verify-email/", {"token": token})
        self.assertEqual(response.status_code, 200)
        self.second.refresh_from_db()
        self.assertTrue(self.second.email_verified)
        response = self.client.get(self.auth_url + "/me/")
        self.assertEqual(response.json()["user"]["id"], self.first.pk)

    @patch("apps.users.services.email_service.send_verification_email", return_value=True)
    def test_deleted_verified_email_can_register_without_inheriting_verification(self, send_email):
        email = self.first.email
        old_token = self.first.generate_verification_token()
        old_refresh_token = str(RefreshToken.for_user(self.first))
        self.first.delete()
        response = self.client.post("/api/users/register/", {"email": email, "password": "example-password"})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertFalse(response.json()["user"]["email_verified"])
        send_email.assert_called_once()

        response = self.client.post(self.auth_url + "/verify-email/", {"token": old_token})
        self.assertEqual(response.status_code, 400)
        self.client.cookies[settings.AUTH_COOKIE_REFRESH] = old_refresh_token
        response = self.client.post(self.auth_url + "/refresh/")
        self.assertEqual(response.status_code, 401)

    def test_existing_email_signup_explains_how_to_sign_in(self):
        response = self.client.post(
            "/api/users/register/", {"email": self.first.email.upper(), "password": "example-password"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Sign in", response.json()["email"][0])

    def test_switching_accounts_reads_only_the_current_own_profile(self):
        browser = APIClient(enforce_csrf_checks=True)
        csrf_token = browser.get(self.auth_url + "/csrf/").json()["csrfToken"]
        self.assertEqual(browser.post(self.auth_url + "/login/", {
            "email": self.first.email, "password": "example-password",
        }).status_code, 200)
        self.assertEqual(browser.get("/api/users/profile/").json()["user"]["username"], "first")
        browser.cookies.pop(settings.AUTH_COOKIE_ACCESS)
        self.assertEqual(browser.post(self.auth_url + "/logout/", HTTP_X_CSRFTOKEN=csrf_token).status_code, 200)
        self.assertEqual(browser.cookies[settings.AUTH_COOKIE_REFRESH].value, "")
        self.assertEqual(browser.post(self.auth_url + "/login/", {
            "email": self.second.email, "password": "example-password",
        }).status_code, 200)
        self.assertEqual(browser.get("/api/users/profile/").json()["user"]["username"], "second")

    def test_other_user_profile_discloses_no_private_fields_and_cannot_be_deleted(self):
        browser = APIClient()
        browser.force_authenticate(self.second)
        for endpoint in ("/api/users/profile/first/", "/api/users/profiles/first/"):
            data = browser.get(endpoint).json()
            self.assertNotIn("email", data["user"])
            self.assertNotIn("date_of_birth", data)
        self.assertEqual(browser.delete("/api/users/profiles/first/").status_code, 404)
        self.assertEqual(browser.patch("/api/users/profiles/first/", {"bio": "changed"}).status_code, 404)

    def test_legacy_follow_route_respects_private_profile_approval(self):
        self.first.profile.visibility = Visibility.PRIVATE
        self.first.profile.save(update_fields=["visibility"])
        browser = APIClient()
        browser.force_authenticate(self.second)

        response = browser.post("/api/users/profiles/first/follow/")

        self.assertTrue(response.json()["follow_request_pending"])
        self.assertTrue(FollowRequest.objects.filter(follower=self.second.profile, following=self.first.profile).exists())
        self.assertFalse(Follow.objects.filter(follower=self.second.profile, following=self.first.profile).exists())


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
