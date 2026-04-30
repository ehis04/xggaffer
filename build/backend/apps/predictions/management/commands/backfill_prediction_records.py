from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.livefootball.models import Competition, CompetitionFixture
from apps.predictions.models import PredictionRecord
from apps.predictions.views.match_prediction_widget import (
    OUTCOME_MAP,
    ENGINE_2_VERSION,
    _confidence_band,
    explain_match,
)
from apps.predictions.data_collection.config.team_name_mappings import CANONICAL_TEAM_NAMES

# Build a lookup from any provider alias → Understat canonical name.
# Covers short names like "Milan" → "AC Milan", "Man City" → "Manchester City", etc.
_PROVIDER_TO_UNDERSTAT: dict[str, str] = {}
for _canonical, _aliases in CANONICAL_TEAM_NAMES.items():
    _understat = _aliases.get("understat", _canonical)
    _PROVIDER_TO_UNDERSTAT[_canonical] = _understat
    for _alias in _aliases.values():
        _PROVIDER_TO_UNDERSTAT[_alias] = _understat


def _to_understat(name: str) -> str:
    """Normalise a team name from any provider to its Understat equivalent."""
    return _PROVIDER_TO_UNDERSTAT.get(name, name)


# Supplementary aliases not covered by CANONICAL_TEAM_NAMES.
# These are short/display names used by football-data.org fixtures.
_EXTRA_ALIASES: dict[str, str] = {
    # EPL
    "Nottingham": "Nottingham Forest",
    "Brighton Hove": "Brighton",
    # La Liga
    "Athletic": "Athletic Club",
    "Atleti": "Atletico Madrid",
    "Barça": "Barcelona",
    # Bundesliga
    "Bayern": "Bayern Munich",
    "Bremen": "Werder Bremen",
    "Frankfurt": "Eintracht Frankfurt",
    "HSV": "Hamburger SV",
    # Serie A
    "AC Pisa": "Pisa",
    # Ligue 1
    "Olympique Lyon": "Lyon",
    "PSG": "Paris Saint Germain",
    "Paris Saint-Germain": "Paris Saint Germain",
}
_PROVIDER_TO_UNDERSTAT.update(_EXTRA_ALIASES)

_logger = logging.getLogger(__name__)

LEAGUE_COMPETITION_CODE = {
    "EPL": "PL",
    "La_Liga": "PD",
    "Bundesliga": "BL1",
    "Serie_A": "SA",
    "Ligue_1": "FL1",
}

ACTUAL_OUTCOME_MAP = {
    "H": lambda h, a: h > a,
    "D": lambda h, a: h == a,
    "A": lambda h, a: a > h,
}


def _derive_actual_result(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "H"
    if away_score > home_score:
        return "A"
    return "D"


class Command(BaseCommand):
    help = (
        "Backfill PredictionRecord for all completed 2025/26 fixtures across "
        "all 5 leagues. Skips fixtures that already have a matching record. "
        "Resolves each record immediately against the known result."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--league",
            choices=list(LEAGUE_COMPETITION_CODE.keys()) + ["all"],
            default="all",
        )
        parser.add_argument("--season", default="2025")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created without writing to the DB.",
        )
        parser.add_argument(
            "--delete-existing",
            action="store_true",
            help="Delete all existing PredictionRecord rows before backfilling.",
        )

    def handle(self, *args, **options):
        league_arg = options["league"]
        season = options["season"]
        dry_run = options["dry_run"]
        delete_existing = options["delete_existing"]

        leagues = (
            list(LEAGUE_COMPETITION_CODE.keys())
            if league_arg == "all"
            else [league_arg]
        )

        if delete_existing and not dry_run:
            deleted, _ = PredictionRecord.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing PredictionRecord rows."))

        total_created = 0
        total_skipped = 0
        total_failed = 0

        for league_code in leagues:
            comp_code = LEAGUE_COMPETITION_CODE[league_code]
            self.stdout.write(f"\n── {league_code} ({comp_code}) ──")

            try:
                comp = Competition.objects.get(code=comp_code)
            except Competition.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Competition {comp_code} not found, skipping."))
                continue

            fixtures = list(
                CompetitionFixture.objects.filter(
                    competition=comp,
                    season_label=season,
                    home_score__isnull=False,
                    away_score__isnull=False,
                ).order_by("kickoff_at")
            )

            self.stdout.write(f"  {len(fixtures)} completed fixtures found.")

            league_created = 0
            league_skipped = 0
            league_failed = 0

            for fixture in fixtures:
                home = _to_understat(fixture.home_team_name)
                away = _to_understat(fixture.away_team_name)

                already_exists = PredictionRecord.objects.filter(
                    home_team=home,
                    away_team=away,
                    league_code=league_code,
                    actual_result__isnull=False,
                ).exists()

                if already_exists:
                    league_skipped += 1
                    continue

                try:
                    result = explain_match(home, away, league_code, season, top_n=5)
                except Exception as exc:
                    _logger.warning("explain_match failed for %s vs %s: %s", home, away, exc)
                    league_failed += 1
                    continue

                probs = result.get("probabilities", {})
                home_prob = probs.get("home", 0.0)
                draw_prob = probs.get("draw", 0.0)
                away_prob = probs.get("away", 0.0)
                max_prob = max(home_prob, draw_prob, away_prob)
                prediction = result.get("prediction", "")
                predicted_outcome = OUTCOME_MAP.get(prediction, "H")
                band = _confidence_band(max_prob)

                actual_result = _derive_actual_result(fixture.home_score, fixture.away_score)
                correct = predicted_outcome == actual_result

                if dry_run:
                    self.stdout.write(
                        f"  [DRY RUN] {home} vs {away}: pred={predicted_outcome} "
                        f"actual={actual_result} correct={correct} band={band}"
                    )
                    league_created += 1
                    continue

                try:
                    PredictionRecord.objects.create(
                        home_team=home,
                        away_team=away,
                        league_code=league_code,
                        predicted_home_prob=home_prob,
                        predicted_draw_prob=draw_prob,
                        predicted_away_prob=away_prob,
                        predicted_outcome=predicted_outcome,
                        confidence_band=band,
                        engine_version=ENGINE_2_VERSION,
                        actual_result=actual_result,
                        resolved_at=fixture.kickoff_at or timezone.now(),
                        correct=correct,
                    )
                    league_created += 1
                except Exception as exc:
                    _logger.error("PredictionRecord create failed for %s vs %s: %s", home, away, exc)
                    league_failed += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"  created={league_created} skipped={league_skipped} failed={league_failed}"
                )
            )
            total_created += league_created
            total_skipped += league_skipped
            total_failed += league_failed

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No records written."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDone. created={total_created} skipped={total_skipped} failed={total_failed}"
                )
            )