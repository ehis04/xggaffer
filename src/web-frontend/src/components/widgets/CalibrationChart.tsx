import NullStatePlaceholder from './NullStatePlaceholder';
import type { ConfidenceBucketAccuracy, MarketComparison } from '../../services/api/widgetApi';
import styles from './css/CalibrationChart.module.css';

const RANDOM_BASELINE_PCT = 33.3;
const MODEL_ACCURACY_BASELINE_PCT = 52.4;
const CHART_BAR_MAX_HEIGHT_PX = 160;

const BAND_LABEL: Record<string, string> = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
};

function toHeightPx(accuracy: number | null): number {
  if (accuracy === null) return 0;
  return (accuracy / 100) * CHART_BAR_MAX_HEIGHT_PX;
}

function toRefLinePx(pct: number): number {
  return CHART_BAR_MAX_HEIGHT_PX - (pct / 100) * CHART_BAR_MAX_HEIGHT_PX;
}

interface CalibrationChartProps {
  buckets: ConfidenceBucketAccuracy[];
  marketComparison?: MarketComparison | null;
}

export default function CalibrationChart({ buckets, marketComparison }: CalibrationChartProps) {
  if (!buckets || buckets.length === 0) {
    return (
      <NullStatePlaceholder icon="chart" message="Calibration data not available" />
    );
  }

  const randomRefTop = toRefLinePx(RANDOM_BASELINE_PCT);
  const modelRefTop = toRefLinePx(MODEL_ACCURACY_BASELINE_PCT);
  const marketAccuracyPct = marketComparison?.market_accuracy != null
    ? Math.round(marketComparison.market_accuracy * 100)
    : null;
  const marketRefTop = marketAccuracyPct !== null ? toRefLinePx(marketAccuracyPct) : null;

  return (
    <div className={styles.wrapper}>
      <div className={styles.referenceRow}>
        <div className={`${styles.referenceItem} ${styles.referenceItemLeft}`}>
          <span className={`${styles.referenceSwatch} ${styles.referenceSwatchRandom}`} aria-hidden="true" />
          <span className={styles.referenceText}>Random ({RANDOM_BASELINE_PCT}%)</span>
        </div>
        {marketAccuracyPct !== null ? (
          <div className={`${styles.referenceItem} ${styles.referenceItemCenter}`}>
            <span className={`${styles.referenceSwatch} ${styles.referenceSwatchMarket}`} aria-hidden="true" />
            <span className={styles.referenceText}>Market ({marketAccuracyPct}%)</span>
          </div>
        ) : (
          <div className={`${styles.referenceItem} ${styles.referenceItemCenter} ${styles.referenceItemGhost}`} aria-hidden="true" />
        )}
        <div className={`${styles.referenceItem} ${styles.referenceItemRight}`}>
          <span className={`${styles.referenceSwatch} ${styles.referenceSwatchModel}`} aria-hidden="true" />
          <span className={styles.referenceText}>Model avg ({MODEL_ACCURACY_BASELINE_PCT}%)</span>
        </div>
      </div>

      <div className={styles.chartArea} style={{ height: CHART_BAR_MAX_HEIGHT_PX }}>
          <div
            className={styles.refLine}
            style={{ top: randomRefTop }}
            aria-hidden="true"
          />
          <div
            className={styles.refLine}
            style={{ top: modelRefTop }}
            aria-hidden="true"
          />
          {marketRefTop !== null && (
            <div
              className={`${styles.refLine} ${styles.refLineMarket}`}
              style={{ top: marketRefTop }}
              aria-hidden="true"
            />
          )}

        <div className={styles.bars}>
          {buckets.map(bucket => {
            const accuracyPct = bucket.accuracy !== null
              ? Math.round(bucket.accuracy * 100)
              : null;
            const barHeight = toHeightPx(accuracyPct);

            return (
              <div
                key={bucket.band}
                className={styles.barGroup}
              >
                <span className={styles.accuracyLabel}>
                  {accuracyPct !== null ? `${accuracyPct}%` : 'No data'}
                </span>
                <div
                  className={styles.barTrack}
                  style={{ height: CHART_BAR_MAX_HEIGHT_PX }}
                >
                  <div
                    className={`${styles.bar} ${styles[bucket.band]}`}
                    style={{ height: barHeight }}
                  />
                </div>
                <span className={styles.sampleSize}>(n={bucket.total})</span>
                <span className={styles.bandLabel}>{BAND_LABEL[bucket.band] ?? bucket.band}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}