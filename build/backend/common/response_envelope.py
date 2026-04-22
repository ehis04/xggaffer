from __future__ import annotations

from typing import Optional

from common.freshness import FreshnessPayload
from common.utils import iso_or_none, utcnow

ENVELOPE_VERSION = '1'


def build_envelope(
    data,
    freshness_payload: FreshnessPayload,
    version: str = ENVELOPE_VERSION,
    warnings: Optional[list] = None,
) -> dict:
    return {
        'data': data,
        'freshness': freshness_payload.to_dict(),
        'version': version,
        'warnings': warnings or [],
        'generated_at': iso_or_none(utcnow()),
    }


def build_degraded_envelope(
    freshness_payload: FreshnessPayload,
    version: str = ENVELOPE_VERSION,
    message: str = 'Data temporarily unavailable.',
) -> dict:
    return {
        'data': None,
        'freshness': freshness_payload.to_dict(),
        'version': version,
        'warnings': [message],
        'generated_at': iso_or_none(utcnow()),
        'degraded': True,
    }