import NullStatePlaceholder from './NullStatePlaceholder';
import type { ConfidenceDistributionBucket } from '../../services/api/widgetApi';
import styles from './css/ConfidenceAccuracyChart.module.css';

const RANDOM_BASELINE = 33.3;
const CHART_HEIGHT_PX = 160;
const BAR_WIDTH_PX = 52;

interface Props {
  buckets: ConfidenceDistributionBucket[];
  overallAccuracy?: number;
  marketAccuracy?: number | null;
}

function toBarHeightPx(accuracy: number): number {
  return (accuracy / 100) * CHART_HEIGHT_PX;
}

function toRefTopPx(pct: number): number {
  return CHART_HEIGHT_PX - (pct / 100) * CHART_HEIGHT_PX;
}

function formatBucket(min: number, max: number): string {
  return `${Math.round(min * 100)}–${Math.round(max * 100)}%`;
}

export default function ConfidenceAccuracyChart({ buckets, overallAccuracy, marketAccuracy }: Props) {
  const populated = buckets.filter(b => b.total > 0);

  if (!populated.length) {
    return <NullStatePlaceholder icon="chart" message="Not enough data to plot confidence accuracy" />;
  }

  const randomRefTop = toRefTopPx(RANDOM_BASELINE);
  const overallRefTop = overallAccuracy != null
    ? toRefTopPx(Math.round(overallAccuracy * 100))
    : null;
  const marketRefTop = marketAccuracy != null
    ? toRefTopPx(Math.round(marketAccuracy * 100))
    : null;

  return (
    <div className={styles.wrapper}>
      <div className={styles.chartArea} style={{ height: CHART_HEIGHT_PX }}>
        <div className={styles.refLine} style={{ top: randomRefTop }} aria-hidden="true">
          <span className={styles.refLabel}>Random ({RANDOM_BASELINE}%)</span>
        </div>
        {overallRefTop !== null && (
          <div className={`${styles.refLine} ${styles.refLineModel}`} style={{ top: overallRefTop }} aria-hidden="true">
            <span className={`${styles.refLabel} ${styles.refLabelModel} ${styles.refLabelLeft}`}>
              Models ({Math.round((overallAccuracy ?? 0) * 100)}%)
            </span>
          </div>
        )}
        {marketRefTop !== null && (
          <div className={`${styles.refLine} ${styles.refLineMarket}`} style={{ top: marketRefTop }} aria-hidden="true">
            <span className={`${styles.refLabel} ${styles.refLabelMarket} ${styles.refLabelRight}`}>
              Market ({Math.round((marketAccuracy ?? 0) * 100)}%)
            </span>
          </div>
        )}

        <div className={styles.bars}>
          {populated.map((bucket, i) => {
            const accuracyPct = bucket.accuracy !== null
              ? Math.round(bucket.accuracy * 100)
              : null;
            const barHeight = accuracyPct !== null ? toBarHeightPx(accuracyPct) : 0;
            const aboveOverall = overallAccuracy != null && bucket.accuracy != null
              && bucket.accuracy > overallAccuracy;

            return (
              <div key={i} className={styles.barGroup} style={{ width: BAR_WIDTH_PX }}>
                <span className={styles.accuracyLabel}>
                  {accuracyPct !== null ? `${accuracyPct}%` : '–'}
                </span>
                <div className={styles.barTrack} style={{ height: CHART_HEIGHT_PX }}>
                  <div
                    className={`${styles.bar} ${aboveOverall ? styles.barAbove : styles.barBelow}`}
                    style={{ height: barHeight }}
                  />
                </div>
                <span className={styles.sampleSize}>n={bucket.total}</span>
                <span className={styles.bucketLabel}>
                  {formatBucket(bucket.bucket_min, bucket.bucket_max)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}