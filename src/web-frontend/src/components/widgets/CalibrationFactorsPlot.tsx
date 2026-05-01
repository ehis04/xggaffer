import NullStatePlaceholder from './NullStatePlaceholder';
import type { CalibrationFactorPlot, CalibrationFactor, CalibrationFactorSeries } from '../../services/api/widgetApi';
import styles from './css/CalibrationFactorsPlot.module.css';

type FactorKey = 'accuracy' | 'confidence' | 'brier_score' | 'log_loss';

const METRIC_DESCRIPTION: Record<FactorKey, string> = {
  accuracy:    'Share of predictions with the correct outcome',
  confidence:  'Average model confidence on predicted outcome',
  brier_score: 'Mean squared probability error — lower is better',
  log_loss:    'Probabilistic scoring loss — lower is better',
};

const SERIES_STYLE: Record<string, { bar: string; dot: string; label: string }> = {
  random: { bar: styles.barRandom, dot: styles.dotRandom, label: 'Random baseline' },
  market: { bar: styles.barMarket, dot: styles.dotMarket, label: 'Market'           },
  model:  { bar: styles.barModel,  dot: styles.dotModel,  label: 'Model'            },
};

function formatValue(key: FactorKey, val: number): string {
  if (key === 'accuracy' || key === 'confidence') return `${(val * 100).toFixed(1)}%`;
  return val.toFixed(3);
}

function barWidthPct(
  val: number,
  allVals: number[],
  higherIsBetter: boolean,
): number {
  const finite = allVals.filter(Number.isFinite);
  if (finite.length === 0) return 0;
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (max === min) return 60;
  const normalised = higherIsBetter
    ? (val - min) / (max - min)
    : (max - val) / (max - min);
  // Scale between 20% and 100% so even the weakest bar is visible
  return 20 + normalised * 80;
}

function isBest(val: number, allVals: number[], higherIsBetter: boolean): boolean {
  const finite = allVals.filter(Number.isFinite);
  if (finite.length === 0) return false;
  return higherIsBetter
    ? val === Math.max(...finite)
    : val === Math.min(...finite);
}

interface MetricCardProps {
  factor: CalibrationFactor;
  series: CalibrationFactorSeries[];
}

function MetricCard({ factor, series }: MetricCardProps) {
  const key = factor.key as FactorKey;
  const allVals = series.map(s => s.values[key]).filter((v): v is number => typeof v === 'number');

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardTitle}>{factor.label}</span>
        <span className={styles.cardDirection}>
          {factor.higher_is_better ? '↑ higher better' : '↓ lower better'}
        </span>
      </div>
      <p className={styles.cardDesc}>{METRIC_DESCRIPTION[key]}</p>

      <div className={styles.rows}>
        {series.map(s => {
          const raw = s.values[key];
          if (typeof raw !== 'number' || !Number.isFinite(raw)) {
            return (
              <div key={s.key} className={styles.row}>
                <span className={`${styles.dot} ${SERIES_STYLE[s.key]?.dot ?? ''}`} />
                <span className={styles.rowLabel}>{SERIES_STYLE[s.key]?.label ?? s.label}</span>
                <span className={styles.noData}>—</span>
              </div>
            );
          }

          const width = barWidthPct(raw, allVals, factor.higher_is_better);
          const best = isBest(raw, allVals, factor.higher_is_better);

          return (
            <div key={s.key} className={`${styles.row} ${best ? styles.rowBest : ''}`}>
              <span className={`${styles.dot} ${SERIES_STYLE[s.key]?.dot ?? ''}`} />
              <span className={styles.rowLabel}>{SERIES_STYLE[s.key]?.label ?? s.label}</span>
              <div className={styles.barTrack}>
                <div
                  className={`${styles.bar} ${SERIES_STYLE[s.key]?.bar ?? ''}`}
                  style={{ width: `${width}%` }}
                />
              </div>
              <span className={`${styles.value} ${best ? styles.valueBest : ''}`}>
                {formatValue(key, raw)}
                {best && <span className={styles.bestBadge}>best</span>}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface Props {
  plot: CalibrationFactorPlot | null | undefined;
}

export default function CalibrationFactorsPlot({ plot }: Props) {
  if (!plot || !plot.factors?.length || !plot.series?.length) {
    return <NullStatePlaceholder icon="chart" message="Calibration factor data not available" />;
  }

  const usableFactors = plot.factors.filter(f =>
    ['accuracy', 'confidence', 'brier_score', 'log_loss'].includes(f.key)
  );
  if (usableFactors.length === 0) {
    return <NullStatePlaceholder icon="chart" message="Calibration factor data not available" />;
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.grid}>
        {usableFactors.map(factor => (
          <MetricCard key={factor.key} factor={factor} series={plot.series} />
        ))}
      </div>
    </div>
  );
}
