from unittest.mock import Mock

from django.test import SimpleTestCase, override_settings
from requests.exceptions import Timeout

from services.providers.understat.client import UnderstatClient
from services.providers.understat.exceptions import (
    UnderstatMalformedResponseError,
    UnderstatNotFoundError,
    UnderstatRequestError,
)


class UnderstatClientTests(SimpleTestCase):
    @override_settings(
        UNDERSTAT_BASE_URL="https://understat.example",
        UNDERSTAT_TIMEOUT_SECONDS=9,
        UNDERSTAT_RETRY_COUNT=0,
        UNDERSTAT_USER_AGENT="xgGaffer-test-agent",
    )
    def test_get_match_roster_prefers_ajax_endpoint_when_available(self):
        session = Mock()

        response = Mock()
        response.status_code = 200
        response.text = '{"rosters":{"h":{"1":{"player":"Home GK"}},"a":{"2":{"player":"Away GK"}}}}'
        session.request.return_value = response

        client = UnderstatClient(session=session)
        roster = client.get_match_roster("29058")

        self.assertIn("h", roster)
        self.assertIn("a", roster)
        self.assertEqual(session.request.call_count, 1)
        self.assertEqual(
            session.request.call_args.kwargs["url"],
            "https://understat.example/getMatchData/29058",
        )

    @override_settings(
        UNDERSTAT_BASE_URL="https://understat.example",
        UNDERSTAT_TIMEOUT_SECONDS=9,
        UNDERSTAT_RETRY_COUNT=0,
        UNDERSTAT_USER_AGENT="xgGaffer-test-agent",
    )
    def test_get_match_roster_falls_back_to_html_payload_when_ajax_missing(self):
        session = Mock()

        ajax_response = Mock()
        ajax_response.status_code = 200
        ajax_response.text = '{"shots": []}'

        html_response = Mock()
        html_response.status_code = 200
        html_response.text = """
            <html>
                <script>
                    var rostersData = {"h": {"1": {"player": "Home GK"}}, "a": {"2": {"player": "Away GK"}}};
                </script>
            </html>
        """

        session.request.side_effect = [ajax_response, html_response]

        client = UnderstatClient(session=session)
        roster = client.get_match_roster("29058")

        self.assertIn("h", roster)
        self.assertIn("a", roster)
        self.assertEqual(session.request.call_count, 2)
        first_call = session.request.call_args_list[0].kwargs
        second_call = session.request.call_args_list[1].kwargs
        self.assertEqual(first_call["url"], "https://understat.example/getMatchData/29058")
        self.assertEqual(second_call["url"], "https://understat.example/match/29058")

    @override_settings(
        UNDERSTAT_BASE_URL="https://understat.example",
        UNDERSTAT_TIMEOUT_SECONDS=9,
        UNDERSTAT_RETRY_COUNT=1,
        UNDERSTAT_USER_AGENT="xgGaffer-test-agent",
    )
    def test_get_team_season_payload_prefers_ajax_endpoint_when_available(self):
        session = Mock()

        response = Mock()
        response.status_code = 200
        response.text = '{"players":[{"id":"7","player_name":"Bukayo Saka"}],"statistics":{"result":{}},"dates":[{"id":"m1"}]}'
        session.request.return_value = response

        client = UnderstatClient(session=session)
        payload = client.get_team_season_payload("Arsenal", "2024")

        self.assertEqual(payload["players"][0]["id"], "7")
        self.assertEqual(payload["dates"][0]["id"], "m1")
        self.assertEqual(session.request.call_count, 1)
        self.assertEqual(
            session.request.call_args.kwargs["url"],
            "https://understat.example/getTeamData/Arsenal/2024",
        )

    @override_settings(
        UNDERSTAT_BASE_URL="https://understat.example",
        UNDERSTAT_TIMEOUT_SECONDS=9,
        UNDERSTAT_RETRY_COUNT=1,
        UNDERSTAT_USER_AGENT="xgGaffer-test-agent",
    )
    def test_get_team_season_payload_uses_expected_endpoint_and_extracts_payloads(self):
        session = Mock()

        response = Mock()
        response.status_code = 200
        response.text = """
            <html>
                <script>
                    var playersData = [{"id":"7","player_name":"Bukayo Saka"}];
                    var history = [{"result":"w","scored":"2","missed":"1","xG":"1.40"}];
                    var datesData = [{"id":"match-1"}];
                </script>
            </html>
        """
        session.request.return_value = response

        client = UnderstatClient(session=session)
        payload = client.get_team_season_payload("Arsenal", "2024")

        self.assertEqual(payload["team_external_id"], "Arsenal")
        self.assertEqual(payload["season"], "2024")
        self.assertEqual(payload["players"][0]["id"], "7")
        self.assertEqual(payload["stats"][0]["result"], "w")
        self.assertEqual(payload["dates"][0]["id"], "match-1")

        self.assertEqual(session.request.call_count, 2)
        first_call = session.request.call_args_list[0].kwargs
        second_call = session.request.call_args_list[1].kwargs

        self.assertEqual(first_call["method"], "GET")
        self.assertEqual(first_call["url"], "https://understat.example/getTeamData/Arsenal/2024")
        self.assertEqual(first_call["timeout"], 9)
        self.assertEqual(first_call["headers"]["X-Requested-With"], "XMLHttpRequest")

        self.assertEqual(second_call["method"], "GET")
        self.assertEqual(second_call["url"], "https://understat.example/team/Arsenal/2024")
        self.assertEqual(second_call["timeout"], 9)

    @override_settings(
        UNDERSTAT_BASE_URL="https://understat.example",
        UNDERSTAT_TIMEOUT_SECONDS=5,
        UNDERSTAT_RETRY_COUNT=0,
        UNDERSTAT_USER_AGENT="xgGaffer-test-agent",
    )
    def test_not_found_response_maps_to_understat_not_found_error(self):
        session = Mock()

        response = Mock()
        response.status_code = 404
        response.text = "Not found"
        session.request.return_value = response

        client = UnderstatClient(session=session)

        with self.assertRaises(UnderstatNotFoundError):
            client.get_player_stats("9999")

    @override_settings(
        UNDERSTAT_BASE_URL="https://understat.example",
        UNDERSTAT_TIMEOUT_SECONDS=5,
        UNDERSTAT_RETRY_COUNT=1,
        UNDERSTAT_USER_AGENT="xgGaffer-test-agent",
    )
    def test_timeout_is_retried_then_raised_as_request_error(self):
        session = Mock()
        session.request.side_effect = [
            Timeout("first timeout"),
            Timeout("second timeout"),
            Timeout("third timeout"),
            Timeout("fourth timeout"),
        ]

        client = UnderstatClient(session=session)

        with self.assertRaises(UnderstatRequestError):
            client.get_league_teams("EPL", "2024")

        # 2 attempts for the AJAX path + 2 attempts for the HTML fallback path.
        self.assertEqual(session.request.call_count, 4)

    @override_settings(
        UNDERSTAT_BASE_URL="https://understat.example",
        UNDERSTAT_TIMEOUT_SECONDS=5,
        UNDERSTAT_RETRY_COUNT=0,
        UNDERSTAT_USER_AGENT="xgGaffer-test-agent",
    )
    def test_missing_expected_payload_raises_malformed_response_error(self):
        session = Mock()

        response = Mock()
        response.status_code = 200
        response.text = """
            <html>
                <script>
                    var irrelevantData = [{"x": 1}];
                </script>
            </html>
        """
        session.request.return_value = response

        client = UnderstatClient(session=session)

        with self.assertRaises(UnderstatMalformedResponseError):
            client.get_team_season_payload("Arsenal", "2024")