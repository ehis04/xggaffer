/**
 * OverviewDataState.tsx
 *
 * Generic loading / error / empty state block used by LiveFootballBasePage
 * while the overview is fetching or when it fails.
 *
 * CSS: LiveFootballBasePage.module.css  (prefix: lfb-)
 */

import React from 'react';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

// ─── Props ────────────────────────────────────────────────────────────────────

interface OverviewDataStateProps {
  title: string;
  description: string;
  variant?: 'neutral' | 'error' | 'empty';
}

// ─── Component ────────────────────────────────────────────────────────────────

const OverviewDataState: React.FC<OverviewDataStateProps> = ({
  title,
  description,
  variant = 'neutral',
}) => {
  const surfaceClass =
    variant === 'error'
      ? `${styles['lfb-section-surface']} ${styles['lfb-section-surface-error']}`
      : styles['lfb-section-surface'];

  return (
    <section className={surfaceClass}>
      <div className={styles['lfb-section-heading-group']}>
        <h2 className={styles['lfb-section-title']}>{title}</h2>
        <p className={styles['lfb-section-subtitle']}>{description}</p>
      </div>
    </section>
  );
};

export default OverviewDataState;