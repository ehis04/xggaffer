/**
 * AllTimeStreaksPreview.tsx
 *
 * Two-column preview of the longest all-time and longest current winning
 * streaks across tracked competitions.
 *
 * CSS: LiveFootballBasePage.module.css  (prefix: lfb-)
 */

import React from 'react';
import type {
  LiveFootballAllTimeStreaks,
  LiveFootballStreakCard,
} from '../../../types/livefootball';
import SectionFrame from './SectionFrame';
import { buildLiveFootballLink } from './linking';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatUpdatedAt = (value: string | null): string | null => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
};

// ─── StreakCard sub-component ─────────────────────────────────────────────────

const StreakCard: React.FC<{
  item: LiveFootballStreakCard;
  variantLabel: string;
}> = ({ item, variantLabel }) => (
  <article className={styles['lfb-streak-card']}>
    <div className={styles['lfb-streak-top-row']}>
      <div className={styles['lfb-streak-identity']}>
        <div className={styles['lfb-streak-variant']}>{variantLabel}</div>
        <div className={styles['lfb-streak-team-name']}>{item.team_name}</div>
        <div className={styles['lfb-streak-competition-name']}>
          {item.competition_name || item.competition_code || 'Streak record'}
        </div>
      </div>

      <div className={styles['lfb-streak-value-block']}>
        <div className={styles['lfb-streak-value']}>{item.streak_value ?? '-'}</div>
        <div className={styles['lfb-streak-value-label']}>matches</div>
      </div>
    </div>

    <div className={styles['lfb-streak-summary']}>{item.summary}</div>
  </article>
);

// ─── Props ────────────────────────────────────────────────────────────────────

interface AllTimeStreaksPreviewProps {
  data: LiveFootballAllTimeStreaks;
}

// ─── Component ────────────────────────────────────────────────────────────────

const AllTimeStreaksPreview: React.FC<AllTimeStreaksPreviewProps> = ({ data }) => {
  const allTimeItems = data.all_time ?? [];
  const currentItems = data.current ?? [];

  if (allTimeItems.length === 0 && currentItems.length === 0) return null;

  const updatedAtLabel = formatUpdatedAt(data.updated_at);
  const ctaTo = buildLiveFootballLink(data.cta.path, data.cta.query);

  return (
    <SectionFrame
      title="All-time streaks"
      subtitle="Longest all-time and current winning streak previews."
      actionLabel={data.cta.label}
      actionTo={ctaTo}
      meta={
        updatedAtLabel ? (
          <span className={styles['lfb-meta-text']}>Updated {updatedAtLabel}</span>
        ) : undefined
      }
    >
      <div className={styles['lfb-streak-columns']}>
        {allTimeItems.length > 0 && (
          <div className={styles['lfb-streak-column']}>
            <div className={styles['lfb-streak-column-header']}>
              <h3 className={styles['lfb-streak-column-title']}>Longest all-time</h3>
            </div>
            <div className={styles['lfb-streak-list']}>
              {allTimeItems.map((item) => (
                <StreakCard key={`all-${item.team_name}`} item={item} variantLabel="All-time" />
              ))}
            </div>
          </div>
        )}

        {currentItems.length > 0 && (
          <div className={styles['lfb-streak-column']}>
            <div className={styles['lfb-streak-column-header']}>
              <h3 className={styles['lfb-streak-column-title']}>Longest current</h3>
            </div>
            <div className={styles['lfb-streak-list']}>
              {currentItems.map((item) => (
                <StreakCard key={`cur-${item.team_name}`} item={item} variantLabel="Current" />
              ))}
            </div>
          </div>
        )}
      </div>
    </SectionFrame>
  );
};

export default AllTimeStreaksPreview;