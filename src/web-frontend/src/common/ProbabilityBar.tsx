import styles from './css/ProbabilityBar.module.css';

interface ProbabilitySet {
  home: number;
  draw: number;
  away: number;
}

interface ProbabilityBarProps {
  probabilities: ProbabilitySet;
  label?: string;
  homeLabel?: string;
  drawLabel?: string;
  awayLabel?: string;
}

const clampPercentage = (value: number): number => {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, value * 100));
};

const formatPercentage = (value: number): number => Math.round(clampPercentage(value));

export default function ProbabilityBar({
  probabilities,
  label,
  homeLabel = 'Home',
  drawLabel = 'Draw',
  awayLabel = 'Away',
}: ProbabilityBarProps) {
  const homeWidth = clampPercentage(probabilities.home);
  const drawWidth = clampPercentage(probabilities.draw);
  const awayWidth = clampPercentage(probabilities.away);

  const homeDisplay = formatPercentage(probabilities.home);
  const drawDisplay = formatPercentage(probabilities.draw);
  const awayDisplay = formatPercentage(probabilities.away);

  return (
    <div className={styles.wrapper}>
      {label && <p className={styles.label}>{label}</p>}

      <div className={styles.probBar}>
        <div className={styles.probSegmentHome} style={{ width: `${homeWidth}%` }}>
          {homeLabel} {homeDisplay}%
        </div>
        <div className={styles.probSegmentDraw} style={{ width: `${drawWidth}%` }}>
          {drawLabel} {drawDisplay}%
        </div>
        <div className={styles.probSegmentAway} style={{ width: `${awayWidth}%` }}>
          {awayLabel} {awayDisplay}%
        </div>
      </div>
    </div>
  );
}