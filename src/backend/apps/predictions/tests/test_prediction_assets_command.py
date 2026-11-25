from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.predictions.management.commands.check_prediction_assets import (
    DATA_FILE_GROUPS,
    MODEL_GROUPS,
)


class CheckPredictionAssetsCommandTests(SimpleTestCase):
    def test_strict_mode_fails_when_assets_are_missing(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(CommandError):
                call_command("check_prediction_assets", data_dir=Path(directory), strict=True)

    def test_strict_mode_passes_when_every_asset_group_exists(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for _, candidates in DATA_FILE_GROUPS:
                asset = root / candidates[0]
                asset.parent.mkdir(parents=True, exist_ok=True)
                asset.touch()
            for _, pattern in MODEL_GROUPS:
                asset = root / "models" / pattern.replace("*", "test")
                asset.parent.mkdir(parents=True, exist_ok=True)
                asset.touch()

            call_command("check_prediction_assets", data_dir=root, strict=True)
