import UncertaintyNote from './UncertaintyNote';
import type { BiggestMiss, BiggestHit } from '../../services/api/widgetApi';
import styles from './css/BiggestMissesPanel.module.css';

type PanelVariant = 'miss' | 'hit';

interface Props {
  items: BiggestMiss[] | BiggestHit[];
  variant: PanelVariant;
}

function formatDate(isoStr: string): string {
  return new Date(isoStr).toLocaleDateString(undefined, {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

function pct(val: number): string {
  return `${Math.round(val * 100)}%`;
}

export default function BiggestMissesPanel({ items, variant }: Props) {
  if (!items || items.length === 0) {
    return (
      <UncertaintyNote
        message={variant === 'miss' ? 'No high-confidence misses recorded' : 'No high-confidence hits recorded'}
      />
    );
  }

  const isMiss = variant === 'miss';

  return (
    <div className={styles.panel}>
      {items.map((item, i) => (
        <div key={i} className={isMiss ? styles.missRow : styles.hitRow}>
          <div className={styles.missHeader}>
            <span className={styles.fixture}>
              {item.home_team} vs {item.away_team}
            </span>
            <span className={isMiss ? styles.missBadge : styles.hitBadge}>
              {isMiss ? 'High confidence miss' : 'High confidence hit'}
            </span>
          </div>
          <div className={styles.missDetail}>
            <span className={styles.missDetailItem}>
              Predicted: <strong>{item.predicted_outcome}</strong>
            </span>
            <span className={styles.confidenceChip}>
              {pct(item.max_confidence)} confidence
            </span>
            <span className={styles.missDetailItem}>
              Actual: <strong>{item.actual_result}</strong>
            </span>
            {isMiss && (
              <span className={styles.offBy}>
                off by {pct(item.off_by)}
              </span>
            )}
            <span className={styles.missDate}>{formatDate(item.predicted_at)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}