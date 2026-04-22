import type { FreshnessPayload } from '../types/freshness';

export type FreshnessState = 'fresh' | 'stale' | 'degraded' | 'unknown';

export function getFreshnessState(freshness: FreshnessPayload | null | undefined): FreshnessState {
  if (!freshness) return 'unknown';
  if (freshness.is_degraded) return 'degraded';
  if (freshness.is_stale) return 'stale';
  return 'fresh';
}

export function formatLastUpdated(freshness: FreshnessPayload | null | undefined): string | null {
  const dt = freshness?.snapshot_published_at ?? freshness?.source_fetched_at;
  if (!dt) return null;
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return null;
  }
}