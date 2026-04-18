import React from 'react';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

interface OverviewDataStateProps {
  title: string;
  description: string;
  variant?: 'neutral' | 'error' | 'empty';
}

const OverviewDataState: React.FC<OverviewDataStateProps> = ({
  title,
  description,
  variant = 'neutral',
}) => {
  const surfaceClassName =
    variant === 'error'
      ? `${styles.sectionSurface} ${styles.sectionSurfaceError}`
      : styles.sectionSurface;

  return (
    <section className={surfaceClassName}>
      <div className={styles.sectionHeadingGroup}>
        <h2 className={styles.sectionTitle}>{title}</h2>
        <p className={styles.sectionSubtitle}>{description}</p>
      </div>
    </section>
  );
};

export default OverviewDataState;