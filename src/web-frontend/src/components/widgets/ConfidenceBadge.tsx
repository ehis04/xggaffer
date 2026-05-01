import styles from './css/ConfidenceBadge.module.css';

interface ConfidenceBadgeProps {
  band: 'high' | 'medium' | 'low';
  score: number;
}

const BAND_LABEL: Record<'high' | 'medium' | 'low', string> = {
  high: 'High confidence',
  medium: 'Medium confidence',
  low: 'Low confidence',
};

export default function ConfidenceBadge({ band, score }: ConfidenceBadgeProps) {
  return (
    <span
      className={`${styles.badge} ${styles[band]}`}
      title={`Confidence score: ${(score * 100).toFixed(1)}%`}
    >
      {BAND_LABEL[band]}
    </span>
  );
}