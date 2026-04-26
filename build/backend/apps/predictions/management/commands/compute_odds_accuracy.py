from __future__ import annotations

from datetime import timezone

from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils import timezone as tz

from apps.livefootball.models import Competition, CompetitionFixture
from apps.predictions.models import FixtureOddsSnapshot, OddsAccuracyStats
from apps.predictions.services.prediction_helper import build_match_prediction_payload
from apps.predictions.services.odds.service import OddsComparisonService
from apps.predictions.views_core import (
    _LEAGUE_COMPETITION_CODE,
    _lf_to_snapshot,
    _snap_to_canonical,
)

ALL_LEAGUES = list(_LEAGUE_COMPETITION_CODE.keys())


class Command(BaseCommand):
    help = (
        "Pre-compute model vs market accuracy stats for completed fixtures with odds data. "
        "Compares which source assigned higher probability to the actual outcome."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--league',
            choices=ALL_LEAGUES + ['all'],
            default='all',
        )
        parser.add_argument('--season', default='2025')

    def handle(self, *args, **options):
        league_arg = options['league']
        season = options['season']
        leagues = ALL_LEAGUES if league_arg == 'all' else [league_arg]
        odds_service = OddsComparisonService()
        now = tz.now()

        for league in leagues:
            self.stdout.write(f'\n── {league} {season} ──')
            result = self._compute_league(league, season, now, odds_service)
            OddsAccuracyStats.objects.update_or_create(
                league=league,
                season=season,
                defaults={
                    'model_wins': result['model_wins'],
                    'market_wins': result['market_wins'],
                    'ties': result['ties'],
                    'total_evaluated': result['total_evaluated'],
                },
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  model={result['model_wins']}  market={result['market_wins']}  "
                    f"ties={result['ties']}  total={result['total_evaluated']}  "
                    f"skipped={result['skipped']}"
                )
            )

    def _compute_league(self, league: str, season: str, now, odds_service) -> dict:
        comp_code = _LEAGUE_COMPETITION_CODE.get(league)
        result_map: dict[tuple[str, str], str] = {}

        if comp_code:
            try:
                comp = Competition.objects.get(code=comp_code)
                for f in CompetitionFixture.objects.filter(
                    competition=comp,
                    season_label=season,
                    home_score__isnull=False,
                    away_score__isnull=False,
                ):
                    h = _lf_to_snapshot(f.home_team_name)
                    a = _lf_to_snapshot(f.away_team_name)
                    hg, ag = f.home_score, f.away_score
                    outcome = 'H' if hg > ag else 'A' if ag > hg else 'D'
                    result_map[(h, a)] = outcome
            except Competition.DoesNotExist:
                pass

        latest_ids = (
            FixtureOddsSnapshot.objects
            .filter(league=league, season=season)
            .values('external_fixture_id')
            .annotate(latest_id=Max('id'))
            .values_list('latest_id', flat=True)
        )
        past_snapshots = (
            FixtureOddsSnapshot.objects
            .filter(id__in=latest_ids, commence_time__lt=now)
            .prefetch_related('quotes__bookmaker')
            .order_by('commence_time')
        )

        model_wins = market_wins = ties = total = skipped = 0
        seen: set[tuple[str, str]] = set()

        for snap in past_snapshots:
            key = (_snap_to_canonical(snap.home_team), _snap_to_canonical(snap.away_team))
            if key in seen:
                continue
            seen.add(key)

            outcome = result_map.get(key)
            if not outcome:
                skipped += 1
                continue

            quotes = list(snap.quotes.all())
            if not quotes:
                skipped += 1
                continue

            quote_rows = [
                {
                    'bookmaker': q.bookmaker.name,
                    'home_odds': q.home_odds,
                    'draw_odds': q.draw_odds,
                    'away_odds': q.away_odds,
                    'devig_home': q.devig_home,
                    'devig_draw': q.devig_draw,
                    'devig_away': q.devig_away,
                    'last_seen_at': q.last_seen_at.isoformat() if q.last_seen_at else None,
                }
                for q in quotes
            ]
            consensus = odds_service.get_consensus_market_view(quote_rows)
            outcome_key = 'home' if outcome == 'H' else 'away' if outcome == 'A' else 'draw'
            market_prob_key = f'consensus_{outcome_key}_probability'
            market_prob = consensus.get(market_prob_key)
            if market_prob is None:
                skipped += 1
                continue

            try:
                pred = build_match_prediction_payload(
                    home_team=key[0],
                    away_team=key[1],
                    league=league,
                    season=season,
                )
                model_prob = pred['probabilities'][outcome_key]
            except Exception:
                skipped += 1
                continue

            total += 1
            if model_prob > market_prob:
                model_wins += 1
            elif market_prob > model_prob:
                market_wins += 1
            else:
                ties += 1

        return {
            'model_wins': model_wins,
            'market_wins': market_wins,
            'ties': ties,
            'total_evaluated': total,
            'skipped': skipped,
        }
