import pytest
from unittest.mock import patch

from apps.livefootball.envelope import build_livefootball_envelope
from common.freshness import FreshnessPayload

REQUIRED_ENVELOPE_KEYS = {'data', 'freshness', 'version', 'warnings', 'generated_at'}
REQUIRED_FRESHNESS_KEYS = {
    'source_fetched_at', 'snapshot_published_at', 'is_stale',
    'is_degraded', 'stale_reason', 'sla_seconds',
}


@pytest.mark.django_db
class TestBuildLivefootballEnvelope:
    def test_has_all_required_keys(self):
        env = build_livefootball_envelope({'league_order': []})
        assert REQUIRED_ENVELOPE_KEYS.issubset(env.keys())

    def test_freshness_has_all_required_keys(self):
        env = build_livefootball_envelope({'league_order': []})
        assert REQUIRED_FRESHNESS_KEYS.issubset(env['freshness'].keys())

    def test_data_field_preserved(self):
        payload = {'league_order': ['PL', 'PD'], 'top_performing_teams': []}
        env = build_livefootball_envelope(payload)
        assert env['data'] == payload

    def test_warnings_defaults_to_empty_list(self):
        env = build_livefootball_envelope({})
        assert env['warnings'] == []

    def test_warnings_passed_through(self):
        env = build_livefootball_envelope({}, warnings=['Data may be incomplete.'])
        assert 'Data may be incomplete.' in env['warnings']

    def test_generated_at_is_string(self):
        env = build_livefootball_envelope({})
        assert isinstance(env['generated_at'], str)

    def test_no_active_snapshot_gives_stale(self):
        env = build_livefootball_envelope({})
        assert env['freshness']['is_stale'] is True
        assert env['freshness']['stale_reason'] == 'no_snapshot_published'

    def test_version_is_present(self):
        env = build_livefootball_envelope({})
        assert env['version'] == '1'

    def test_degraded_with_none_data_returns_degraded_envelope(self):
        degraded_fp = FreshnessPayload(
            source_fetched_at=None,
            snapshot_published_at=None,
            is_stale=True,
            is_degraded=True,
            stale_reason='no_snapshot_published',
            sla_seconds=1800,
        )
        with patch(
            'apps.livefootball.envelope.compute_surface_freshness',
            return_value=degraded_fp,
        ):
            env = build_livefootball_envelope(None)
            assert env['data'] is None
            assert env.get('degraded') is True