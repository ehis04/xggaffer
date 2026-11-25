from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.predictions.data_paths import data_root_from_environment


class DataRootTests(SimpleTestCase):
    def test_environment_override_is_used(self):
        with patch.dict(os.environ, {"XGGAFFER_DATA_DIR": "/srv/xggaffer-data"}):
            self.assertEqual(data_root_from_environment(), Path("/srv/xggaffer-data"))

    def test_repository_data_directory_is_the_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            root = data_root_from_environment()

        expected = Path(__file__).resolve().parents[5] / "data"
        self.assertEqual(root, expected)
