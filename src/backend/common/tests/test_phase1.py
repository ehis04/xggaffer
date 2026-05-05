from __future__ import annotations

import pytest
from datetime import timedelta
from unittest.mock import patch

from common.freshness import FreshnessPayload, compute_freshness, is_within_sla
from common.response_envelopes import build_envelope, build_degraded_envelope
from common.provider_policy import (
    exponential_backoff_seconds,
    get_lock_key,
    is_budget_safe,
    budget_remaining,
)
from common.utils import age_seconds, is_older_than, iso_or_none, latest_of, utcnow
from common import constants, sync_constants, exceptions


# ---------------------------------------------------------------------------
# freshness.py
# ---------------------------------------------------------------------------

class TestComputeFreshness:
    def test_no_snapshot_published(self):
        fp = compute_freshness(None, None, sla_seconds=900)
        assert fp.is_stale is True
        assert fp.stale_reason == 'no_snapshot_published'
        assert fp.snapshot_published_at is None

    def test_within_sla(self):
        now = utcnow()
        published_at = now - timedelta(seconds=300)
        fp = compute_freshness(now, published_at, sla_seconds=900)
        assert fp.is_stale is False
        assert fp.stale_reason is None

    def test_beyond_sla(self):
        now = utcnow()
        published_at = now - timedelta(seconds=1800)
        fp = compute_freshness(now, published_at, sla_seconds=900)
        assert fp.is_stale is True
        assert fp.stale_reason == 'sla_exceeded'

    def test_degraded_when_failures_at_threshold(self):
        fp = compute_freshness(None, None, sla_seconds=900, consecutive_failures=3, degraded_threshold=3)
        assert fp.is_degraded is True

    def test_not_degraded_below_threshold(self):
        fp = compute_freshness(None, None, sla_seconds=900, consecutive_failures=2, degraded_threshold=3)
        assert fp.is_degraded is False

    def test_to_dict_serialises_datetimes_as_strings(self):
        now = utcnow()
        fp = compute_freshness(now, now, sla_seconds=900)
        d = fp.to_dict()
        assert isinstance(d['source_fetched_at'], str)
        assert isinstance(d['snapshot_published_at'], str)


class TestIsWithinSla:
    def test_none_published_at_returns_false(self):
        assert is_within_sla(None, 900) is False

    def test_within_sla_returns_true(self):
        published_at = utcnow() - timedelta(seconds=300)
        assert is_within_sla(published_at, 900) is True

    def test_beyond_sla_returns_false(self):
        published_at = utcnow() - timedelta(seconds=1800)
        assert is_within_sla(published_at, 900) is False


# ---------------------------------------------------------------------------
# response_envelopes.py
# ---------------------------------------------------------------------------

class TestBuildEnvelope:
    def _make_freshness(self):
        return compute_freshness(None, None, sla_seconds=900)

    def test_envelope_has_required_keys(self):
        fp = self._make_freshness()
        env = build_envelope(data={'x': 1}, freshness_payload=fp)
        assert set(env.keys()) >= {'data', 'freshness', 'version', 'warnings', 'generated_at'}

    def test_warnings_defaults_to_empty_list(self):
        fp = self._make_freshness()
        env = build_envelope(data={}, freshness_payload=fp, warnings=None)
        assert env['warnings'] == []

    def test_generated_at_is_non_null_string(self):
        fp = self._make_freshness()
        env = build_envelope(data={}, freshness_payload=fp)
        assert isinstance(env['generated_at'], str)
        assert len(env['generated_at']) > 0

    def test_data_preserved(self):
        fp = self._make_freshness()
        payload = {'league': 'PL', 'matchweek': 30}
        env = build_envelope(data=payload, freshness_payload=fp)
        assert env['data'] == payload


class TestBuildDegradedEnvelope:
    def _make_freshness(self):
        return compute_freshness(None, None, sla_seconds=900, consecutive_failures=5, degraded_threshold=3)

    def test_data_is_none(self):
        fp = self._make_freshness()
        env = build_degraded_envelope(fp)
        assert env['data'] is None

    def test_degraded_key_is_true(self):
        fp = self._make_freshness()
        env = build_degraded_envelope(fp)
        assert env['degraded'] is True

    def test_warnings_contains_message(self):
        fp = self._make_freshness()
        env = build_degraded_envelope(fp, message='Service unavailable.')
        assert 'Service unavailable.' in env['warnings']


# ---------------------------------------------------------------------------
# provider_policy.py
# ---------------------------------------------------------------------------

class TestBudgetHelpers:
    def test_at_90_percent_is_not_safe(self):
        assert is_budget_safe(90, 100, safety_margin=0.10) is False

    def test_below_90_percent_is_safe(self):
        assert is_budget_safe(89, 100, safety_margin=0.10) is True

    def test_zero_used_is_safe(self):
        assert is_budget_safe(0, 100, safety_margin=0.10) is True

    def test_budget_remaining(self):
        assert budget_remaining(30, 100) == 70

    def test_budget_remaining_floored_at_zero(self):
        assert budget_remaining(150, 100) == 0


class TestExponentialBackoff:
    def test_attempt_zero_within_expected_range(self):
        delay = exponential_backoff_seconds(0, base=2.0, jitter=False)
        assert delay == 1.0

    def test_capped_at_max(self):
        delay = exponential_backoff_seconds(100, base=2.0, jitter=False, cap=300.0)
        assert delay == 300.0

    def test_jitter_result_is_positive(self):
        delay = exponential_backoff_seconds(2, base=2.0, jitter=True)
        assert delay > 0


class TestGetLockKey:
    def test_format(self):
        key = get_lock_key('understat', 'fixtures', 'PL_2024')
        assert key == 'sync_lock:understat:fixtures:PL_2024'


# ---------------------------------------------------------------------------
# Import isolation — confirm no circular imports
# ---------------------------------------------------------------------------

class TestImportIsolation:
    def test_constants_importable(self):
        from common import constants
        assert hasattr(constants, 'ProviderName')
        assert hasattr(constants, 'SyncStatus')

    def test_sync_constants_importable(self):
        from common import sync_constants
        assert hasattr(sync_constants, 'DEFAULT_MAX_RETRIES')

    def test_freshness_importable(self):
        from common import freshness
        assert hasattr(freshness, 'compute_freshness')

    def test_response_envelopes_importable(self):
        from common import response_envelopes
        assert hasattr(response_envelopes, 'build_envelope')

    def test_provider_policy_importable(self):
        from common import provider_policy
        assert hasattr(provider_policy, 'is_budget_safe')

    def test_exceptions_importable(self):
        from common import exceptions
        assert hasattr(exceptions, 'StaleSnapshotUnavailable')