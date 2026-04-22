from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.predictions.models import (
    Bookmaker,
    FixtureOddsSnapshot,
    BookmakerQuote,
    HistoricalMarketBenchmark,
)


class OddsModelTests(TestCase):
    def setUp(self):
        self.bookmaker = Bookmaker.objects.create(
            name='Bet365',
            slug='bet365',
            source=Bookmaker.Source.THE_ODDS_API,
            region='eu',
            is_active=True,
        )

        self.snapshot = FixtureOddsSnapshot.objects.create(
            bookmaker_source=Bookmaker.Source.THE_ODDS_API,
            external_fixture_id='fixture-123',
            league='Premier League',
            season='2025',
            home_team='Arsenal',
            away_team='Liverpool',
            commence_time=timezone.now(),
        )

    def test_bookmaker_can_be_created(self):
        self.assertEqual(self.bookmaker.name, 'Bet365')
        self.assertEqual(self.bookmaker.slug, 'bet365')
        self.assertTrue(self.bookmaker.is_active)

    def test_fixture_odds_snapshot_can_be_created(self):
        self.assertEqual(self.snapshot.external_fixture_id, 'fixture-123')
        self.assertEqual(self.snapshot.market_type, FixtureOddsSnapshot.MarketType.MATCH_RESULT)
        self.assertFalse(self.snapshot.is_consensus_snapshot)

    def test_bookmaker_quote_links_to_snapshot_and_bookmaker(self):
        quote = BookmakerQuote.objects.create(
            snapshot=self.snapshot,
            bookmaker=self.bookmaker,
            home_odds=2.1,
            draw_odds=3.4,
            away_odds=3.2,
            implied_home=0.4762,
            implied_draw=0.2941,
            implied_away=0.3125,
            devig_home=0.4396,
            devig_draw=0.2714,
            devig_away=0.2890,
        )

        self.assertEqual(quote.snapshot, self.snapshot)
        self.assertEqual(quote.bookmaker, self.bookmaker)

    def test_duplicate_bookmaker_quote_for_same_snapshot_fails(self):
        BookmakerQuote.objects.create(
            snapshot=self.snapshot,
            bookmaker=self.bookmaker,
            home_odds=2.1,
            draw_odds=3.4,
            away_odds=3.2,
            implied_home=0.4762,
            implied_draw=0.2941,
            implied_away=0.3125,
            devig_home=0.4396,
            devig_draw=0.2714,
            devig_away=0.2890,
        )

        with self.assertRaises(IntegrityError):
            BookmakerQuote.objects.create(
                snapshot=self.snapshot,
                bookmaker=self.bookmaker,
                home_odds=2.2,
                draw_odds=3.5,
                away_odds=3.1,
                implied_home=0.4545,
                implied_draw=0.2857,
                implied_away=0.3226,
                devig_home=0.4270,
                devig_draw=0.2685,
                devig_away=0.3045,
            )

    def test_historical_market_benchmark_allows_null_market_metrics(self):
        benchmark = HistoricalMarketBenchmark.objects.create(
            league='Premier League',
            season='2025',
            sample_size=360,
            model_accuracy=0.555,
            market_favourite_accuracy=None,
            model_brier_score=None,
            market_brier_score=None,
            evaluation_scope='season_backtest',
            source_label='engine4_backtest',
        )

        self.assertIsNone(benchmark.market_favourite_accuracy)
        self.assertIsNone(benchmark.model_brier_score)
        self.assertIsNone(benchmark.market_brier_score)