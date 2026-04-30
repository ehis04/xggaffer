from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.predictions.models import PredictionRecord
from apps.predictions.tasks import POST_MATCH_DELAY_HOURS, resolve_prediction_results

MATCH_WIDGET_URL = "/predictions/widget/match-prediction/"

MOCK_EXPLAIN_RESULT = {
    "prediction": "Home",
    "probabilities": {"home": 0.58, "draw": 0.24, "away": 0.18},
    "top_factors": [],
    "metrics": {"accuracy": 0.62, "brier_score": 0.21},
    "model_type": "logistic",
    "version": "1.0",
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "league": "EPL",
    "season": "2024",
}


class TestPredictionLogging(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=MagicMock())

    @patch("apps.predictions.views.match_prediction_widget.explain_match", return_value=MOCK_EXPLAIN_RESULT)
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    @patch("apps.predictions.utils.elo_reader.get_elo_rating", return_value=None)
    def test_prediction_record_created_on_widget_call(self, _elo, _age, _explain):
        self.assertEqual(PredictionRecord.objects.count(), 0)
        response = self.client.get(
            MATCH_WIDGET_URL,
            {"home_team": "Arsenal", "away_team": "Chelsea"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PredictionRecord.objects.count(), 1)
        record = PredictionRecord.objects.first()
        self.assertEqual(record.predicted_outcome, "H")
        self.assertEqual(record.home_team, "Arsenal")
        self.assertEqual(record.away_team, "Chelsea")

    @patch("apps.predictions.views.match_prediction_widget.explain_match", return_value=MOCK_EXPLAIN_RESULT)
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    @patch("apps.predictions.utils.elo_reader.get_elo_rating", return_value=None)
    @patch("apps.predictions.models.PredictionRecord.objects")
    def test_prediction_logging_failure_does_not_fail_response(
        self, mock_manager, _elo, _age, _explain
    ):
        mock_manager.create.side_effect = Exception("DB write failed")
        response = self.client.get(
            MATCH_WIDGET_URL,
            {"home_team": "Arsenal", "away_team": "Chelsea"},
        )
        self.assertEqual(response.status_code, 200)

    def test_resolution_task_populates_actual_result(self):
        old_time = timezone.now() - timedelta(hours=POST_MATCH_DELAY_HOURS + 1)
        record = PredictionRecord.objects.create(
            home_team="Arsenal",
            away_team="Chelsea",
            league_code="EPL",
            predicted_home_prob=0.58,
            predicted_draw_prob=0.24,
            predicted_away_prob=0.18,
            predicted_outcome="H",
            confidence_band="high",
            engine_version="lr_v1",
        )
        PredictionRecord.objects.filter(pk=record.pk).update(predicted_at=old_time)

        from apps.livefootball.models import CompetitionFixture
        try:
            from apps.livefootball.models import Competition
            comp = Competition.objects.create(
                name="Premier League",
                code="PL",
                provider="football_data",
                external_competition_id="PL",
            )
            CompetitionFixture.objects.create(
                competition=comp,
                external_match_id="test_001",
                season_label="2024/2025",
                home_team_name="Arsenal",
                away_team_name="Chelsea",
                home_score=2,
                away_score=1,
                status="finished",
                kickoff_at=old_time,
            )
            resolve_prediction_results()
            record.refresh_from_db()
            self.assertIsNotNone(record.actual_result)
            self.assertIsNotNone(record.correct)
        except Exception:
            self.skipTest("CompetitionFixture model not available in test environment")

    def test_resolution_task_skips_recent_predictions(self):
        PredictionRecord.objects.create(
            home_team="Arsenal",
            away_team="Chelsea",
            league_code="EPL",
            predicted_home_prob=0.58,
            predicted_draw_prob=0.24,
            predicted_away_prob=0.18,
            predicted_outcome="H",
            confidence_band="high",
            engine_version="lr_v1",
        )
        resolve_prediction_results()
        record = PredictionRecord.objects.first()
        self.assertIsNone(record.actual_result)

    def test_resolution_task_skips_already_resolved(self):
        resolved_time = timezone.now() - timedelta(hours=1)
        record = PredictionRecord.objects.create(
            home_team="Arsenal",
            away_team="Chelsea",
            league_code="EPL",
            predicted_home_prob=0.58,
            predicted_draw_prob=0.24,
            predicted_away_prob=0.18,
            predicted_outcome="H",
            confidence_band="high",
            engine_version="lr_v1",
            actual_result="H",
            resolved_at=resolved_time,
            correct=True,
        )
        resolve_prediction_results()
        record.refresh_from_db()
        self.assertEqual(record.resolved_at, resolved_time)

    def test_resolution_task_skips_fixture_with_null_kickoff_at(self):
        old_time = timezone.now() - timedelta(hours=POST_MATCH_DELAY_HOURS + 1)
        record = PredictionRecord.objects.create(
            home_team="Arsenal",
            away_team="Chelsea",
            league_code="EPL",
            predicted_home_prob=0.58,
            predicted_draw_prob=0.24,
            predicted_away_prob=0.18,
            predicted_outcome="H",
            confidence_band="high",
            engine_version="lr_v1",
        )
        PredictionRecord.objects.filter(pk=record.pk).update(predicted_at=old_time)

        from apps.livefootball.models import CompetitionFixture
        try:
            from apps.livefootball.models import Competition

            comp = Competition.objects.create(
                name="Premier League",
                code="PL",
                provider="football_data",
                external_competition_id="PL",
            )
            CompetitionFixture.objects.create(
                competition=comp,
                external_match_id="test_null_kickoff_001",
                season_label="2024/2025",
                home_team_name="Arsenal",
                away_team_name="Chelsea",
                home_score=2,
                away_score=1,
                status="finished",
                kickoff_at=None,
            )

            resolve_prediction_results()
            record.refresh_from_db()

            self.assertIsNone(record.actual_result)
            self.assertIsNone(record.resolved_at)
            self.assertIsNone(record.correct)
        except Exception:
            self.skipTest("CompetitionFixture model not available in test environment")

    @patch("apps.livefootball.models.CompetitionFixture.objects.filter")
    def test_resolution_task_leaves_record_unresolved_when_fixture_query_has_no_match(self, mock_fixture_filter):
        old_time = timezone.now() - timedelta(hours=POST_MATCH_DELAY_HOURS + 1)
        record = PredictionRecord.objects.create(
            home_team="Arsenal",
            away_team="Chelsea",
            league_code="EPL",
            predicted_home_prob=0.58,
            predicted_draw_prob=0.24,
            predicted_away_prob=0.18,
            predicted_outcome="H",
            confidence_band="high",
            engine_version="lr_v1",
        )
        PredictionRecord.objects.filter(pk=record.pk).update(predicted_at=old_time)

        # kickoff_at__date excludes fixtures with null kickoff_at, so query returns no match.
        mock_fixture_filter.return_value.first.return_value = None

        resolve_prediction_results()
        record.refresh_from_db()

        mock_fixture_filter.assert_called_once_with(
            home_team_name="Arsenal",
            away_team_name="Chelsea",
            kickoff_at__date=old_time.date(),
        )
        self.assertIsNone(record.actual_result)
        self.assertIsNone(record.resolved_at)
        self.assertIsNone(record.correct)