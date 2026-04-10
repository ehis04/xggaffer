import React from 'react';
import { Link } from 'react-router-dom';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

interface LiveFootballHeroHeaderProps {
  generatedAt?: string | null;
}

const formatGeneratedAt = (value?: string | null): string | null => {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date.toLocaleString('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
};

const LiveFootballHeroHeader: React.FC<LiveFootballHeroHeaderProps> = ({
  generatedAt,
}) => {
  const generatedAtLabel = formatGeneratedAt(generatedAt);

  return (
    <section className={styles.heroSurface}>
      <div>
        <h1 className={styles.heroTitle}>Live Football</h1>

        <p className={styles.heroBody}>
          Your live football hub across the six main leagues. Browse league snapshots,
          trend sections, match previews, streaks, and first-versus-last club context
          from one overview page.
        </p>
      </div>

      <div className={styles.heroActions}>
        <Link to="/livefootball/leagues" className={styles.actionButton}>
          View leagues
        </Link>

        <Link
          to="/livefootball/competitions"
          className={`${styles.actionButton} ${styles.actionButtonSecondary}`}
        >
          Open competitions browser
        </Link>
      </div>

      {generatedAtLabel ? (
        <div className={styles.heroMeta}>
          Homepage data generated {generatedAtLabel}
        </div>
      ) : null}
    </section>
  );
};

export default LiveFootballHeroHeader;