import type { FreshnessPayload } from '../types/freshness';
import { isEnvelope } from '../types/response';
import type { ApiEnvelope } from '../types/response';

export { isEnvelope as isApiEnvelope };

export function unwrapEnvelope<T>(value: ApiEnvelope<T>): T {
    if (value.data === null || value.data === undefined) {
        throw new Error('Envelope contains no data');
    }
    return value.data;
}

export function requireFreshness(envelope: ApiEnvelope<unknown>): FreshnessPayload {
    if (envelope.freshness) {
        return envelope.freshness;
    }
    return {
        is_stale: true,
        is_degraded: true,
        stale_reason: 'No freshness data',
        source_fetched_at: null,
        snapshot_published_at: null,
        sla_seconds: 0,
    };
}