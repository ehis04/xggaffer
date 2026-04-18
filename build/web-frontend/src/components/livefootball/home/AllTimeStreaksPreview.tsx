import React from 'react';
import type {
  LiveFootballAllTimeStreaks,
  LiveFootballStreakCard,
} from '../../../types/livefootball';
import SectionFrame from './SectionFrame';
import { buildLiveFootballLink } from './linking';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

interface AllTimeStreaksPreviewProps {
  data: LiveFootballAllTimeStreaks;
}

const formatUpdatedAt = (value: string | null): string | null => {
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

const StreakCard: React.FC<{
  item: LiveFootballStreakCard;
  variantLabel: string;
}> = ({ item, variantLabel }) => {
  return (
    <article className={styles.streakCard}>
      <div className={styles.streakTopRow}>
        <div className={styles.streakIdentity}>
          <div className={styles.streakVariant}>{variantLabel}</div>
          <div className={styles.streakTeamName}>{item.team_name}</div>
          <div className={styles.streakCompetitionName}>
            {item.competition_name || item.competition_code || 'Streak record'}
          </div>
        </div>

        <div className={styles.streakValueBlock}>
          <div className={styles.streakValue}>{item.streak_value ?? '-'}</div>
          <div className={styles.streakValueLabel}>matches</div>
        </div>
      </div>

      <div className={styles.streakSummary}>{item.summary}</div>
    </article>
  );
};

const AllTimeStreaksPreview: React.FC<AllTimeStreaksPreviewProps> = ({
  data,
}) => {
  const allTimeItems = data.all_time ?? [];
  const currentItems = data.current ?? [];

  if (allTimeItems.length === 0 && currentItems.length === 0) {
    return null;
  }

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
          <span className={styles.metaText}>Updated {updatedAtLabel}</span>
        ) : undefined
      }
    >
      <div className={styles.streakColumns}>
        {allTimeItems.length > 0 ? (
          <div className={styles.streakColumn}>
            <div className={styles.streakColumnHeader}>
              <h3 className={styles.streakColumnTitle}>Longest all-time</h3>
            </div>

            <div className={styles.streakList}>
              {allTimeItems.map((item) => (
                <StreakCard
                  key={`all-${item.team_name}`}
                  item={item}
                  variantLabel="All-time"
                />
              ))}
            </div>
          </div>
        ) : null}

        {currentItems.length > 0 ? (
          <div className={styles.streakColumn}>
            <div className={styles.streakColumnHeader}>
              <h3 className={styles.streakColumnTitle}>Longest current</h3>
            </div>

            <div className={styles.streakList}>
              {currentItems.map((item) => (
                <StreakCard
                  key={`cur-${item.team_name}`}
                  item={item}
                  variantLabel="Current"
                />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </SectionFrame>
  );
};

export default AllTimeStreaksPreview;