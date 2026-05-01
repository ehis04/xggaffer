import type { FreshnessPayload } from '../types/freshness';
import { getFreshnessState, formatLastUpdated } from '../utils/freshness';
import styles from './css/FreshnessBadge.module.css';

const STATIC_DATASET_STATUS = 'static_dataset' as const;
const NO_COVERAGE_STATUS = 'no_coverage' as const;

interface ExtendedFreshnessPayload extends FreshnessPayload {
  staleness_status?: string;
}

interface FreshnessBadgeProps {
  freshness: ExtendedFreshnessPayload | null | undefined;
}

export function FreshnessBadge({ freshness }: FreshnessBadgeProps) {
  if (freshness?.staleness_status === NO_COVERAGE_STATUS) {
    return null;
  }

  if (freshness?.staleness_status === STATIC_DATASET_STATUS) {
    return (
      <span className={`${styles.badge} ${styles.static}`}>
        Static dataset
      </span>
    );
  }

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
