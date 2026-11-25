import re

from django.test import SimpleTestCase


class RequestIdMiddlewareTests(SimpleTestCase):
    def test_generates_request_id_for_public_health_route(self):
        response = self.client.get("/health/live/")

        self.assertEqual(response.status_code, 200)
        self.assertRegex(response["X-Request-ID"], r"^[a-f0-9]{32}$")

    def test_preserves_safe_caller_request_id(self):
        response = self.client.get(
            "/health/live/",
            headers={"X-Request-ID": "edge-01.request_42"},
        )

        self.assertEqual(response["X-Request-ID"], "edge-01.request_42")

    def test_replaces_unsafe_request_id(self):
        response = self.client.get(
            "/health/live/",
            headers={"X-Request-ID": "unsafe request id\nforged"},
        )

        self.assertNotEqual(response["X-Request-ID"], "unsafe request id\nforged")
        self.assertTrue(re.fullmatch(r"[a-f0-9]{32}", response["X-Request-ID"]))
