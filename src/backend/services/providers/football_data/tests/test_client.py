from django.test import SimpleTestCase

from services.providers.football_data.client import FootballDataClient
from services.providers.football_data.exceptions import FootballDataRequestError


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, method, url, headers=None, params=None, timeout=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
            }
        )
        return self.response


class FootballDataClientTests(SimpleTestCase):
    def test_get_competitions_passes_area_params(self):
        session = FakeSession(
            FakeResponse(
                payload={
                    "competitions": [
                        {"id": 2021, "name": "Premier League"},
                    ]
                }
            )
        )
        client = FootballDataClient(
            api_token="token",
            base_url="https://api.example.com/v4",
            timeout=15,
            retry_count=0,
            session=session,
        )

        payload = client.get_competitions(areas=[2072, 2088])

        self.assertEqual(payload["competitions"][0]["id"], 2021)
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0]["method"], "GET")
        self.assertEqual(
            session.calls[0]["url"],
            "https://api.example.com/v4/competitions",
        )
        self.assertEqual(session.calls[0]["params"], {"areas": "2072,2088"})
        self.assertEqual(session.calls[0]["headers"]["X-Auth-Token"], "token")

    def test_get_competition_table_hits_standings_endpoint(self):
        session = FakeSession(
            FakeResponse(
                payload={
                    "competition": {"id": 2021, "name": "Premier League"},
                    "standings": [],
                }
            )
        )
        client = FootballDataClient(
            api_token="token",
            base_url="https://api.example.com/v4",
            retry_count=0,
            session=session,
        )

        payload = client.get_competition_table(2021, season=2025)

        self.assertEqual(payload["competition"]["id"], 2021)
        self.assertEqual(
            session.calls[0]["url"],
            "https://api.example.com/v4/competitions/2021/standings",
        )
        self.assertEqual(session.calls[0]["params"], {"season": 2025})

    def test_get_competition_matches_maps_filters_correctly(self):
        session = FakeSession(
            FakeResponse(
                payload={
                    "matches": [
                        {"id": 1, "status": "SCHEDULED"},
                    ]
                }
            )
        )
        client = FootballDataClient(
            api_token="token",
            base_url="https://api.example.com/v4",
            retry_count=0,
            session=session,
        )

        payload = client.get_competition_matches(
            2021,
            season=2025,
            matchday=15,
            status="SCHEDULED",
            date_from="2026-03-01",
            date_to="2026-03-31",
            stage="REGULAR_SEASON",
            group="A",
        )

        self.assertEqual(payload["matches"][0]["id"], 1)
        self.assertEqual(
            session.calls[0]["url"],
            "https://api.example.com/v4/competitions/2021/matches",
        )
        self.assertEqual(
            session.calls[0]["params"],
            {
                "season": 2025,
                "matchday": 15,
                "status": "SCHEDULED",
                "dateFrom": "2026-03-01",
                "dateTo": "2026-03-31",
                "stage": "REGULAR_SEASON",
                "group": "A",
            },
        )

    def test_get_competition_table_rejects_placeholder_competition_id(self):
        session = FakeSession(FakeResponse(payload={"standings": []}))
        client = FootballDataClient(
            api_token="token",
            base_url="https://api.example.com/v4",
            retry_count=0,
            session=session,
        )

        with self.assertRaises(FootballDataRequestError) as context:
            client.get_competition_table("<PL_EXTERNAL_ID>", season=2025)

        self.assertIn("Invalid competition_id", str(context.exception))
        self.assertEqual(session.calls, [])

    def test_get_competition_scorers_hits_scorers_endpoint(self):
        session = FakeSession(
            FakeResponse(
                payload={
                    "scorers": [
                        {"player": {"id": 9, "name": "Player A"}, "goals": 20},
                    ]
                }
            )
        )
        client = FootballDataClient(
            api_token="token",
            base_url="https://api.example.com/v4",
            retry_count=0,
            session=session,
        )

        payload = client.get_competition_scorers(2021, season=2025, matchday=28)

        self.assertEqual(payload["scorers"][0]["goals"], 20)
        self.assertEqual(
            session.calls[0]["url"],
            "https://api.example.com/v4/competitions/2021/scorers",
        )
        self.assertEqual(session.calls[0]["params"], {"season": 2025, "matchday": 28})