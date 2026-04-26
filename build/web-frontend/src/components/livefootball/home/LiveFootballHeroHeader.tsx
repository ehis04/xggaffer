/**
 * LiveFootballHeroHeader.tsx
 *
 * Full-width hero section at the top of the live football homepage.
 * Shows the page title, a short description, primary navigation actions,
 * and an optional "generated at" timestamp.
 *
 * CSS: LiveFootballBasePage.module.css  (prefix: lfb-)
 */

import React from 'react';
import { Link } from 'react-router-dom';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatGeneratedAt = (value?: string | null): string | null => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
};

// ─── Props ────────────────────────────────────────────────────────────────────

interface LiveFootballHeroHeaderProps {
  generatedAt?: string | null;
}

// ─── Component ────────────────────────────────────────────────────────────────

const LiveFootballHeroHeader: React.FC<LiveFootballHeroHeaderProps> = ({ generatedAt }) => {
  const generatedAtLabel = formatGeneratedAt(generatedAt);

  return (
    <section className={styles['lfb-hero-surface']}>
      <div>
        <h1 className={styles['lfb-hero-title']}>Live Football</h1>
        <p className={styles['lfb-hero-body']}>
          Your live football hub across the six main leagues. Browse league snapshots,
          trend sections, match previews, streaks, and first-versus-last club context
          from one overview page.
        </p>
      </div>

      <div className={styles['lfb-hero-actions']}>
        <Link to="/livefootball/leagues" className={styles['lfb-action-btn']}>
          View leagues
        </Link>
        <Link
          to="/livefootball/competitions"
          className={`${styles['lfb-action-btn']} ${styles['lfb-action-btn-secondary']}`}
        >
          Open competitions browser
        </Link>
      </div>

      {generatedAtLabel && (
        <div className={styles['lfb-hero-meta']}>
          Homepage data generated {generatedAtLabel}
        </div>
      )}
    </section>
  );
};

export default LiveFootballHeroHeader;