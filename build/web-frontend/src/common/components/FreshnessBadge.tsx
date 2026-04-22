import type { FreshnessPayload } from '../types/freshness';
import { getFreshnessState, formatLastUpdated } from '../utils/freshness';
import styles from './css/FreshnessBadge.module.css';

interface FreshnessBadgeProps {
  freshness: FreshnessPayload | null | undefined;
}

export function FreshnessBadge({ freshness }: FreshnessBadgeProps) {
  const state = getFreshnessState(freshness);
  const lastUpdated = formatLastUpdated(freshness);

  if (state === 'unknown') return null;

  const labels: Record<'fresh' | 'stale' | 'degraded', string> = {
    fresh: 'Live',
    stale: 'Stale',
    degraded: 'Data issue',
  };

  return (
    <span className={`${styles.badge} ${styles[state]}`} title={lastUpdated ?? undefined}>
      {labels[state]}
      {state === 'stale' && lastUpdated && (
        <span className={styles.lastUpdated}> · {lastUpdated}</span>
      )}
    </span>
  );
}