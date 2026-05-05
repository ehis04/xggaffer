from __future__ import annotations


class StaleSnapshotUnavailable(Exception):
    def __init__(self, surface: str, published_at=None):
        self.surface = surface
        self.published_at = published_at
        super().__init__(f'Stale snapshot unavailable for surface: {surface}')


class PublicationFailed(Exception):
    def __init__(self, surface: str, reason: str):
        self.surface = surface
        self.reason = reason
        super().__init__(f'Publication failed for {surface}: {reason}')


class ProviderTemporarilyUnavailable(Exception):
    def __init__(self, provider: str, reason: str):
        self.provider = provider
        self.reason = reason
        super().__init__(f'Provider temporarily unavailable: {provider} — {reason}')


class DegradedDataFallbackActive(Exception):
    def __init__(self, surface: str, last_success_at=None):
        self.surface = surface
        self.last_success_at = last_success_at
        super().__init__(f'Degraded fallback active for surface: {surface}')


class SofaScoreSessionExpired(Exception):
    def __init__(self):
        super().__init__('SofaScore session cookie has expired. Manual renewal required.')


class ProviderBudgetExhausted(Exception):
    def __init__(self, provider: str, requests_used: int, daily_limit: int):
        self.provider = provider
        self.requests_used = requests_used
        self.daily_limit = daily_limit
        super().__init__(
            f'Budget exhausted for {provider}: {requests_used}/{daily_limit} requests used'
        )