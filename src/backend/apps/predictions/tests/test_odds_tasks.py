"""Compatibility wrapper for legacy test module path.

The odds task tests were moved under apps.predictions.services.tests, but
some commands still target apps.predictions.tests.test_odds_tasks.
"""

from apps.predictions.services.tests.test_odds_tasks import *  # noqa: F401,F403
