import React from 'react';
import { Link } from 'react-router-dom';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

interface SectionFrameProps {
  title: string;
  subtitle?: string;
  actionLabel?: string;
  actionTo?: string;
  meta?: React.ReactNode;
  children: React.ReactNode;
}

const SectionFrame: React.FC<SectionFrameProps> = ({
  title,
  subtitle,
  actionLabel,
  actionTo,
  meta,
  children,
}) => {
  return (
    <section className={styles.sectionSurface}>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionHeadingGroup}>
          <h2 className={styles.sectionTitle}>{title}</h2>
          {subtitle ? (
            <p className={styles.sectionSubtitle}>{subtitle}</p>
          ) : null}
        </div>

        <div className={styles.sectionHeaderActions}>
          {meta}
          {actionLabel && actionTo ? (
            <Link to={actionTo} className={styles.actionButton}>
              {actionLabel}
            </Link>
          ) : null}
        </div>
      </div>

      {children}
    </section>
  );
};

export default SectionFrame;