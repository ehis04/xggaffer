from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from apps.livefootball.models import (
    Competition,
    CompetitionFixture,
    CompetitionTableSnapshot,
    CompetitionTopScorer,
    PlayerDirectoryEntry,
    TeamDirectoryEntry,
)


DEFAULT_COMPETITION_CODES = ["PL", "PD", "BL1", "SA", "FL1", "ELC"]


class Command(BaseCommand):
    help = (
        "Report livefootball coverage by competition and season, and highlight missing "
        "teams, players, tables, fixtures, or scorers."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--competition-code",
            action="append",
            dest="competition_codes",
            help="Competition code to verify. Use multiple times for multiple leagues.",
        )
        parser.add_argument(
            "--season",
            action="append",
            dest="seasons",
            type=int,
            help="Season year to verify. Use multiple times for multiple seasons.",
        )
        parser.add_argument(
            "--season-start",
            type=int,
            default=2023,
            help="Starting season year when --season is not supplied.",
        )
        parser.add_argument(
            "--season-end",
            type=int,
            required=False,
            help="Ending season year when --season is not supplied. Defaults to the latest numeric current season.",
        )
        parser.add_argument(
            "--provider",
            default="football_data",
            help="Competition provider slug to verify.",
        )
        parser.add_argument(
            "--fail-on-missing",
            action="store_true",
            help="Exit with a non-zero status when any league-season has missing coverage.",
        )

    def handle(self, *args, **options):
        provider = options["provider"]
        competition_codes = options.get("competition_codes") or DEFAULT_COMPETITION_CODES
        seasons = self._resolve_seasons(
            explicit_seasons=options.get("seasons") or [],
            season_start=options["season_start"],
            season_end=options.get("season_end"),
            provider=provider,
        )

        competitions = {
            competition.code: competition
            for competition in Competition.objects.filter(
                provider=provider,
                code__in=competition_codes,
            )
        }

        missing_competitions = [code for code in competition_codes if code not in competitions]
        if missing_competitions:
            self.stdout.write(
                self.style.WARNING(
                    "Missing competition records for codes: " + ", ".join(missing_competitions)
                )
            )

        missing_coverage = []

        for code in competition_codes:
            competition = competitions.get(code)
            if not competition:
                continue

            self.stdout.write(f"[{code}] {competition.name}")
            for season in seasons:
                season_label = str(season)
                counts = self._get_counts(competition, season_label)
                missing_parts = [
                    label
                    for label in ("teams", "tables", "fixtures", "scorers")
                    if counts[label] == 0
                ]
                if counts["teams"] > 0 and counts["teams_with_players"] < counts["teams"]:
                    missing_parts.append(
                        f"squad directories for {counts['teams'] - counts['teams_with_players']} teams"
                    )
                status = "OK" if not missing_parts else f"MISSING: {', '.join(missing_parts)}"
                self.stdout.write(
                    f"  {season_label} "
                    f"teams={counts['teams']} "
                    f"players={counts['players']} "
                    f"teams_with_players={counts['teams_with_players']} "
                    f"tables={counts['tables']} "
                    f"fixtures={counts['fixtures']} "
                    f"scorers={counts['scorers']} "
                    f"[{status}]"
                )

                if missing_parts:
                    missing_coverage.append((code, season_label, missing_parts))

        if missing_coverage:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Missing livefootball coverage detected:"))
            for code, season_label, missing_parts in missing_coverage:
                self.stdout.write(f"  {code} {season_label}: {', '.join(missing_parts)}")

            if options["fail_on_missing"]:
                raise CommandError("Livefootball coverage is incomplete.")
        else:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Livefootball coverage is complete for the requested range."))

    def _resolve_seasons(self, *, explicit_seasons, season_start, season_end, provider):
        if explicit_seasons:
            return sorted(set(explicit_seasons))

        resolved_end = season_end or self._latest_numeric_current_season(provider)
        if resolved_end < season_start:
            raise CommandError("season-end cannot be earlier than season-start.")
        return list(range(season_start, resolved_end + 1))

    def _latest_numeric_current_season(self, provider):
        season_labels = Competition.objects.filter(provider=provider).values_list(
            "current_season_label", flat=True
        )
        numeric_seasons = [int(label) for label in season_labels if str(label).isdigit()]
        if not numeric_seasons:
            raise CommandError(
                "Could not infer a season-end from Competition.current_season_label. "
                "Pass --season or --season-end explicitly."
            )
        return max(numeric_seasons)

    def _get_counts(self, competition, season_label):
        teams_qs = TeamDirectoryEntry.objects.filter(
            competition=competition,
            season_label=season_label,
        )
        players_qs = PlayerDirectoryEntry.objects.filter(
            team__competition=competition,
            team__season_label=season_label,
        )
        return {
            "teams": teams_qs.count(),
            "players": players_qs.count(),
            "teams_with_players": players_qs.values("team_id").aggregate(
                count=Count("team_id", distinct=True)
            )["count"]
            or 0,
            "tables": CompetitionTableSnapshot.objects.filter(
                competition=competition,
                season_label=season_label,
            ).count(),
            "fixtures": CompetitionFixture.objects.filter(
                competition=competition,
                season_label=season_label,
            ).count(),
            "scorers": CompetitionTopScorer.objects.filter(
                competition=competition,
                season_label=season_label,
            ).count(),
        }