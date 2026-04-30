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
    const parsed = new Date(dt);
    if (Number.isNaN(parsed.getTime())) {
      return null;
    }

    // Render in dd/mm/yyyy with 24-hour time for consistent UI output.
    const formatted = new Intl.DateTimeFormat('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(parsed);

    return formatted.replace(',', '');
  } catch {
    return null;
  }
}