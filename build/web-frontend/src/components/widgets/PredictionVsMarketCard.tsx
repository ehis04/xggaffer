import { FreshnessBadge } from '../../common/components/FreshnessBadge';
import NullStatePlaceholder from './NullStatePlaceholder';
import type { OddsConsensus } from '../../types/prediction';
import type { WidgetFreshness } from '../../services/api/widgetApi';
import styles from './css/PredictionVsMarketCard.module.css';

const ODDS_DIVERGENCE_THRESHOLD = 0.10;
const MARKET_LABEL = 'Bookmaker Market';

interface ModelProbs {
  home: number;
  draw: number;
  away: number;
}

interface PredictionVsMarketCardProps {
  modelProbs: ModelProbs;
  homeTeam: string;
  awayTeam: string;
  marketData: OddsConsensus | null;
  freshness: WidgetFreshness;
}

type Outcome = 'home' | 'draw' | 'away';

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function deltaStr(model: number, market: number): string {
  const diff = (model - market) * 100;
  return diff >= 0 ? `+${diff.toFixed(1)} pp` : `${diff.toFixed(1)} pp`;
}

function isDivergent(model: number, market: number): boolean {
  return Math.abs(model - market) > ODDS_DIVERGENCE_THRESHOLD;
}

interface OutcomeRowProps {
  label: string;
  modelValue: number;
  marketValue: number;
}

function OutcomeRow({ label, modelValue, marketValue }: OutcomeRowProps) {
  const divergent = isDivergent(modelValue, marketValue);
  return (
    <tr className={styles.row}>
      <td className={styles.outcomeLabel}>{label}</td>
      <td className={`${styles.cell} ${divergent ? styles.cellDivergent : ''}`}>
        {pct(modelValue)}
        {divergent && (
          <span className={styles.delta}>{deltaStr(modelValue, marketValue)}</span>
        )}
      </td>
      <td className={styles.cell}>{pct(marketValue)}</td>
    </tr>
  );
}

export default function PredictionVsMarketCard({
  modelProbs,
  homeTeam,
  awayTeam,
  marketData,
  freshness,
}: PredictionVsMarketCardProps) {
  if (!marketData) {
    return (
      <NullStatePlaceholder
        icon="chart"
        message="Odds data not available for this fixture"
      />
    );
  }

  const outcomes: Array<{ label: string; key: Outcome; marketValue: number }> = [
    { label: homeTeam, key: 'home', marketValue: marketData.devig_home },
    { label: 'Draw', key: 'draw', marketValue: marketData.devig_draw },
    { label: awayTeam, key: 'away', marketValue: marketData.devig_away },
  ];

  const modelValues: Record<Outcome, number> = {
    home: modelProbs.home,
    draw: modelProbs.draw,
    away: modelProbs.away,
  };

  return (
    <div className={styles.card}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th} />
            <th className={styles.th}>xgGaffer Model</th>
            <th className={styles.th}>{MARKET_LABEL}</th>
          </tr>
        </thead>
        <tbody>
          {outcomes.map(({ label, key, marketValue }) => (
            <OutcomeRow
              key={key}
              label={label}
              modelValue={modelValues[key]}
              marketValue={marketValue}
            />
          ))}
        </tbody>
      </table>

      <div className={styles.footer}>
        <span className={styles.attribution}>{marketData.source_label}</span>
        <span className={styles.overround}>
          Market margin: {(marketData.overround * 100).toFixed(1)}%
        </span>
        <FreshnessBadge freshness={freshness} />
      </div>
    </div>
  );
}