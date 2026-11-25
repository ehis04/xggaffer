from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.predictions.data_paths import DATA_ROOT


DATA_FILE_GROUPS = (
    (
        "matches",
        (
            "processed/matches/merged/all_leagues_all_seasons_matches_merged.csv",
            "raw/understat/merged/all_leagues_all_seasons_matches.csv",
        ),
    ),
    ("teams", ("processed/teams/merged/all_leagues_all_seasons_teams_merged.csv",)),
    ("players", ("processed/players/merged/all_leagues_all_seasons_players_merged.csv",)),
    ("lineup features", ("processed/lineup_features.csv",)),
)

MODEL_GROUPS = (
    ("match outcome", "match_outcome_logistic_regression_*.joblib"),
    ("scoreline", "score_poisson_dc_*.joblib"),
    ("lineup", "lineup_xgboost_*.joblib"),
    ("availability survival", "survival_cox_v1_*.joblib"),
    ("availability risk", "injury_risk_*_v1_*.joblib"),
    ("tactical pass", "pass_xgboost_*.joblib"),
    ("tactical style", "style_kmeans_*.joblib"),
)


class Command(BaseCommand):
    help = "Check that the datasets and trained model artefacts needed by predictions exist."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            type=Path,
            default=DATA_ROOT,
            help="Override the prediction data root for this check.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit with an error when any asset group is missing.",
        )

    def handle(self, *args, **options):
        data_root: Path = options["data_dir"].expanduser()
        models_root = data_root / "models"
        missing: list[str] = []

        self.stdout.write(f"Prediction data root: {data_root}")

        for label, candidates in DATA_FILE_GROUPS:
            existing = next((data_root / item for item in candidates if (data_root / item).is_file()), None)
            if existing:
                self.stdout.write(self.style.SUCCESS(f"[ok] {label}: {existing}"))
            else:
                missing.append(f"{label} dataset")
                self.stdout.write(self.style.WARNING(f"[missing] {label}: {', '.join(candidates)}"))

        for label, pattern in MODEL_GROUPS:
            matches = sorted(models_root.glob(pattern))
            if matches:
                self.stdout.write(self.style.SUCCESS(f"[ok] {label} model: {matches[-1]}"))
            else:
                missing.append(f"{label} model")
                self.stdout.write(self.style.WARNING(f"[missing] {label} model: models/{pattern}"))

        if missing:
            message = f"Missing {len(missing)} prediction asset group(s): {', '.join(missing)}"
            if options["strict"]:
                raise CommandError(message)
            self.stdout.write(self.style.WARNING(message))
            return

        self.stdout.write(self.style.SUCCESS("All required prediction assets are present."))
