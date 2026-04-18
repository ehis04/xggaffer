from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.livefootball.models import Competition, TeamDirectoryEntry
from services.providers.football_data.exceptions import FootballDataRateLimitError
from services.providers.football_data.sync import (
    sync_competition_fixtures,
    sync_competition_scorers,
    sync_competition_table,
    sync_competition_teams,
    sync_competitions,
    sync_team_squad_directory,
)


class Command(BaseCommand):
    help = (
        "Bootstrap livefootball browse data from football-data: competitions, "
        "teams, team squads (players), fixtures, table, and scorers."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--areas",
            nargs="*",
            type=int,
            default=[2072, 2114, 2081, 2224, 2088],
            help="Area codes to fetch competitions for.",
        )
        parser.add_argument(
            "--competition-id",
            action="append",
            dest="competition_ids",
            help=(
                "Provider competition id to sync full browse data for. "
                "Use multiple times for multiple competitions."
            ),
        )
        parser.add_argument(
            "--season",
            type=int,
            required=False,
            help="Season year used for teams/table/fixtures/scorers endpoints (e.g. 2024).",
        )
        parser.add_argument(
            "--provider",
            default="football_data",
            help="Provider slug used by sync jobs.",
        )
        parser.add_argument(
            "--token",
            required=False,
            help="Optional football-data API token override for this run.",
        )
        parser.add_argument(
            "--max-rate-limit-retries",
            type=int,
            default=5,
            help="Max retries for a sync step when football-data returns 429.",
        )
        parser.add_argument(
            "--cooldown-seconds",
            type=int,
            default=30,
            help="Cooldown wait between rate-limit retries.",
        )
        parser.add_argument(
            "--step-sleep-seconds",
            type=float,
            default=2.0,
            help="Sleep between major competition sync steps.",
        )
        parser.add_argument(
            "--squad-sleep-seconds",
            type=float,
            default=3.0,
            help="Sleep between team squad sync calls.",
        )
        parser.add_argument(
            "--early-stop-after-rate-limit-failures",
            type=int,
            default=3,
            help=(
                "Stop the run after this many consecutive exhausted rate-limit "
                "failures (0 disables early stop)."
            ),
        )

    def handle(self, *args, **options):
        provider = options["provider"]
        areas = options.get("areas") or []
        season = options.get("season")
        token_override = options.get("token")
        competition_ids = options.get("competition_ids") or []
        self.max_rate_limit_retries = max(0, int(options.get("max_rate_limit_retries", 5)))
        self.cooldown_seconds = max(1, int(options.get("cooldown_seconds", 30)))
        self.step_sleep_seconds = max(0.0, float(options.get("step_sleep_seconds", 2.0)))
        self.squad_sleep_seconds = max(0.0, float(options.get("squad_sleep_seconds", 3.0)))
        self.early_stop_after_rate_limit_failures = max(
            0,
            int(options.get("early_stop_after_rate_limit_failures", 3)),
        )
        self._consecutive_exhausted_rate_limits = 0

        if token_override:
            settings.FOOTBALL_DATA_API_TOKEN = token_override

        if not getattr(settings, "FOOTBALL_DATA_API_TOKEN", ""):
            raise CommandError(
                "FOOTBALL_DATA_API_TOKEN is not configured. Set it in backend/.env "
                "or pass --token."
            )

        self.stdout.write(
            f"Syncing competitions for provider={provider}, areas={areas or '-'}"
        )

        try:
            competitions_result = sync_competitions(
                areas=areas or None,
                provider=provider,
            )
        except Exception as exc:
            raise CommandError(f"Failed syncing competitions: {exc}") from exc

        comp_summary = competitions_result["summary"]
        self.stdout.write(self.style.SUCCESS("Competition list sync complete"))
        self.stdout.write(
            f"Processed={comp_summary.get('records_processed', 0)} "
            f"Created={comp_summary.get('records_created', 0)} "
            f"Updated={comp_summary.get('records_updated', 0)} "
            f"Errors={comp_summary.get('error_count', 0)}"
        )

        if competition_ids:
            external_ids = [str(comp_id).strip() for comp_id in competition_ids if str(comp_id).strip()]
        else:
            external_ids = list(
                Competition.objects.filter(provider=provider)
                .exclude(external_id="")
                .values_list("external_id", flat=True)
                .distinct()[:10]
            )

        if not external_ids:
            self.stdout.write("No competitions available to sync browse data for.")
            return

        self.stdout.write(
            f"Syncing browse data for {len(external_ids)} competitions: {', '.join(external_ids)}"
        )

        next_external_id = None
        for external_id in external_ids:
            self.stdout.write("")
            self.stdout.write(f"Competition {provider}:{external_id}")

            step = self._run_sync_step(
                label="teams",
                fn=sync_competition_teams,
                competition_external_id=external_id,
                season=season,
                provider=provider,
            )
            if self._handle_rate_limit_step_result(step, external_id):
                next_external_id = external_id
                break
            self._sleep_between_steps()

            # Sync team squad directories (player listings) after teams are synced
            self.stdout.write("  Syncing team squad directories...")
            squads_step = self._sync_competition_team_squads(
                competition_external_id=external_id,
                season=season,
                provider=provider,
            )
            if self._handle_rate_limit_step_result(squads_step, external_id):
                next_external_id = external_id
                break
            self._sleep_between_steps()

            step = self._run_sync_step(
                label="table",
                fn=sync_competition_table,
                competition_external_id=external_id,
                season=season,
                provider=provider,
            )
            if self._handle_rate_limit_step_result(step, external_id):
                next_external_id = external_id
                break
            self._sleep_between_steps()
            step = self._run_sync_step(
                label="fixtures",
                fn=sync_competition_fixtures,
                competition_external_id=external_id,
                season=season,
                provider=provider,
            )
            if self._handle_rate_limit_step_result(step, external_id):
                next_external_id = external_id
                break
            self._sleep_between_steps()
            step = self._run_sync_step(
                label="scorers",
                fn=sync_competition_scorers,
                competition_external_id=external_id,
                season=season,
                provider=provider,
            )
            if self._handle_rate_limit_step_result(step, external_id):
                next_external_id = external_id
                break
            self._sleep_between_steps()

        if next_external_id is not None:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Early stop triggered due to repeated exhausted rate-limit failures."
                )
            )
            season_arg = f" --season {season}" if season is not None else ""
            self.stdout.write(
                "Resume with: "
                f"python3 manage.py sync_livefootball_bootstrap --competition-id {next_external_id}{season_arg}"
            )
            return

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Livefootball bootstrap sync complete."))

    def _run_sync_step(self, *, label, fn, **kwargs):
        exhausted_rate_limit = False
        for attempt in range(self.max_rate_limit_retries + 1):
            try:
                result = fn(**kwargs)
                summary = result.get("summary", {})
                self.stdout.write(
                    f"  {label}: processed={summary.get('records_processed', 0)} "
                    f"created={summary.get('records_created', 0)} "
                    f"updated={summary.get('records_updated', 0)} "
                    f"errors={summary.get('error_count', 0)}"
                )
                return {"rate_limit_exhausted": False}
            except FootballDataRateLimitError as exc:
                if attempt >= self.max_rate_limit_retries:
                    self.stdout.write(self.style.ERROR(f"  {label}: failed - {exc}"))
                    exhausted_rate_limit = True
                    break
                self._sleep_for_rate_limit(label=label, attempt=attempt + 1)
            except Exception as exc:
                if "rate limit" in str(exc).lower() and attempt < self.max_rate_limit_retries:
                    self._sleep_for_rate_limit(label=label, attempt=attempt + 1)
                    continue
                if "rate limit" in str(exc).lower() and attempt >= self.max_rate_limit_retries:
                    exhausted_rate_limit = True
                self.stdout.write(self.style.ERROR(f"  {label}: failed - {exc}"))
                break
        return {"rate_limit_exhausted": exhausted_rate_limit}

    def _sync_competition_team_squads(self, *, competition_external_id, season, provider):
        """Sync squad directories for all teams in a competition."""
        teams = TeamDirectoryEntry.objects.filter(
            competition__external_id=competition_external_id,
            competition__provider=provider,
        )
        if season is not None:
            teams = teams.filter(season_label=str(season))

        team_external_ids = list(
            teams.exclude(external_id="")
            .values_list("external_id", flat=True)
            .order_by("external_id")
            .distinct()
        )

        if not team_external_ids:
            self.stdout.write("    No teams found to sync squads for.")
            return

        total_created = 0
        total_updated = 0
        total_errors = 0
        processed = 0
        exhausted_rate_limit = False

        for team_external_id in team_external_ids:
            synced = False
            for attempt in range(self.max_rate_limit_retries + 1):
                try:
                    result = sync_team_squad_directory(
                        competition_external_id=competition_external_id,
                        team_external_id=team_external_id,
                        season=season,
                        provider=provider,
                    )
                    summary = result.get("summary", {})
                    processed += summary.get("records_processed", 0)
                    total_created += summary.get("records_created", 0)
                    total_updated += summary.get("records_updated", 0)
                    total_errors += summary.get("error_count", 0)
                    synced = True
                    break
                except FootballDataRateLimitError as exc:
                    if attempt >= self.max_rate_limit_retries:
                        self.stdout.write(self.style.WARNING(f"    Failed to sync squad for team {team_external_id}: {exc}"))
                        total_errors += 1
                        exhausted_rate_limit = True
                        break
                    self._sleep_for_rate_limit(label=f"squads:{team_external_id}", attempt=attempt + 1)
                except Exception as exc:
                    if "rate limit" in str(exc).lower() and attempt < self.max_rate_limit_retries:
                        self._sleep_for_rate_limit(label=f"squads:{team_external_id}", attempt=attempt + 1)
                        continue
                    if "rate limit" in str(exc).lower() and attempt >= self.max_rate_limit_retries:
                        exhausted_rate_limit = True
                    self.stdout.write(self.style.WARNING(f"    Failed to sync squad for team {team_external_id}: {exc}"))
                    total_errors += 1
                    break

            if synced and self.squad_sleep_seconds > 0:
                sleep(self.squad_sleep_seconds)

        self.stdout.write(
            f"    squads: processed={processed} created={total_created} "
            f"updated={total_updated} errors={total_errors}"
        )
        return {"rate_limit_exhausted": exhausted_rate_limit}

    def _sleep_for_rate_limit(self, *, label, attempt):
        self.stdout.write(
            self.style.WARNING(
                f"  {label}: rate-limited, sleeping {self.cooldown_seconds}s before retry "
                f"{attempt}/{self.max_rate_limit_retries}"
            )
        )
        sleep(self.cooldown_seconds)

    def _sleep_between_steps(self):
        if self.step_sleep_seconds > 0:
            sleep(self.step_sleep_seconds)

    def _handle_rate_limit_step_result(self, step_result, competition_external_id):
        if not step_result:
            return False

        if step_result.get("rate_limit_exhausted"):
            self._consecutive_exhausted_rate_limits += 1
        else:
            self._consecutive_exhausted_rate_limits = 0

        if self.early_stop_after_rate_limit_failures == 0:
            return False

        if self._consecutive_exhausted_rate_limits >= self.early_stop_after_rate_limit_failures:
            self.stdout.write(
                self.style.WARNING(
                    f"  Competition {competition_external_id}: reached early-stop threshold "
                    f"({self._consecutive_exhausted_rate_limits} exhausted rate-limit failures)."
                )
            )
            return True

        return False

