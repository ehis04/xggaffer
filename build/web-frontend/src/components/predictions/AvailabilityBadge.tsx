import React from 'react';
import styles from './css/AvailabilityBadge.module.css';

const RISK_THRESHOLDS = { LOW: 0.33, MEDIUM: 0.66 } as const;

const deriveLabelFromScore = (score: number): string => {
  if (score < RISK_THRESHOLDS.LOW) return 'low';
  if (score < RISK_THRESHOLDS.MEDIUM) return 'medium';
  return 'high';
};

interface AvailabilityBadgeProps {
  riskLabel: string | null | undefined;
  riskScore?: number | null;
  isLoading: boolean;
}

const AvailabilityBadge: React.FC<AvailabilityBadgeProps> = ({
  riskLabel,
  riskScore,
  isLoading,
}) => {
  if (isLoading) {
    return <span className={styles.loading} aria-hidden="true" />;
  }

  const resolved = riskLabel?.toLowerCase().trim()
    ?? (riskScore != null ? deriveLabelFromScore(riskScore) : null);

  if (!resolved || !['low', 'medium', 'high'].includes(resolved)) {
    return null;
  }

  const labelClass = resolved as 'low' | 'medium' | 'high';

  return (
    <span className={`${styles.badge} ${styles[labelClass]}`}>
      {resolved.charAt(0).toUpperCase() + resolved.slice(1)}
    </span>
  );
};

export default AvailabilityBadge;