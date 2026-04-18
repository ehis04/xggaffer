import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import type {
  LiveFootballClubSpotlightPlayer,
  LiveFootballFirstVsLastLeagueCard,
  LiveFootballLeagueSnapshotRow,
} from '../../../types/livefootball';
import SectionFrame from './SectionFrame';
import { buildLiveFootballLink } from './linking';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

interface FirstVsLastLeagueSectionProps {
  title: string;
  subtitle?: string;
  actionLabel?: string;
  actionTo?: string;
  items: LiveFootballFirstVsLastLeagueCard[];
  emptyMessage: string;
}

const formatSyncedAt = (value?: string | null): string | null => {
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

const formatFormLabel = (value?: string | null): string => {
  const cleaned = (value || '').trim();
  return cleaned || 'No form data';
};

const formatRecord = (row: LiveFootballLeagueSnapshotRow): string => {
  return `${row.won ?? '-'}-${row.drawn ?? '-'}-${row.lost ?? '-'}`;
};

const FirstVsLastLeagueSection: React.FC<FirstVsLastLeagueSectionProps> = ({
  title,
  subtitle,
  actionLabel,
  actionTo,
  items,
  emptyMessage,
}) => {
  const [index, setIndex] = useState(0);
  const pausedRef = useRef(false);

  useEffect(() => {
    if (index > items.length - 1) {
      setIndex(0);
    }
  }, [items, index]);

  useEffect(() => {
    if (items.length <= 1) {
      return;
    }

    const interval = window.setInterval(() => {
      if (!pausedRef.current) {
        setIndex((current) => (current + 1) % items.length);
      }
    }, 5000);

    return () => window.clearInterval(interval);
  }, [items]);

  if (items.length === 0) {
    return (
      <SectionFrame
        title={title}
        subtitle={subtitle}
        actionLabel={actionLabel}
        actionTo={actionTo}
      >
        <div className={styles.emptyState}>{emptyMessage}</div>
      </SectionFrame>
    );
  }

  const activeItem = items[index];
  const syncedAtLabel = formatSyncedAt(activeItem.synced_at);
  const localActionTo = buildLiveFootballLink(activeItem.cta.path, activeItem.cta.query);

  const handlePrev = (): void => {
    setIndex((current) => (current - 1 + items.length) % items.length);
  };

  const handleNext = (): void => {
    setIndex((current) => (current + 1) % items.length);
  };

  return (
    <div
      onMouseEnter={() => {
        pausedRef.current = true;
      }}
      onMouseLeave={() => {
        pausedRef.current = false;
      }}
    >
      <SectionFrame
        title={title}
        subtitle={subtitle}
        actionLabel={actionLabel}
        actionTo={actionTo}
        meta={
          <span className={styles.metaText}>
            League {index + 1} of {items.length}
          </span>
        }
      >
        <div className={styles.carouselShell}>
          <div className={styles.carouselBody}>
          <div className={styles.matchLeagueSummary}>
            <div className={styles.matchLeagueTitleBlock}>
              <div className={styles.matchLeagueName}>
                {activeItem.competition.name}
              </div>

              <div className={styles.matchLeagueMeta}>
                {activeItem.competition.country || activeItem.competition.code || 'League comparison'}
                {syncedAtLabel ? ` • Updated ${syncedAtLabel}` : ''}
              </div>
            </div>

            <div className={styles.carouselControls}>
              <button
                type="button"
                aria-label="Previous first-v-last league"
                className={styles.carouselButton}
                onClick={handlePrev}
                disabled={items.length <= 1}
              >
                ‹
              </button>

              <span className={styles.carouselIndex}>
                {index + 1}/{items.length}
              </span>

              <button
                type="button"
                aria-label="Next first-v-last league"
                className={styles.carouselButton}
                onClick={handleNext}
                disabled={items.length <= 1}
              >
                ›
              </button>
            </div>
          </div>

          {!activeItem.leader || !activeItem.bottom ? (
            <div className={styles.emptyState}>
              No first-versus-last comparison is available for this league right now.
            </div>
          ) : (
            <>
              <div className={styles.compareGrid}>
                <ComparisonCard
                  row={activeItem.leader}
                  variant="leader"
                  label="League leader"
                />

                <ComparisonCard
                  row={activeItem.bottom}
                  variant="bottom"
                  label="Bottom club"
                />
              </div>

              <div className={styles.spotlightSection}>
                <div className={styles.rowSplit}>
                  <div className={styles.compactTitle}>Spotlight players</div>
                  <div className={styles.metaText}>
                    Quick player context from the leading and trailing sides.
                  </div>
                </div>

                {activeItem.spotlight_players.length === 0 ? (
                  <div className={styles.emptyState}>
                    No spotlight players are available for this league right now.
                  </div>
                ) : (
                  <div className={styles.spotlightGrid}>
                    {activeItem.spotlight_players.map((spotlight, spotlightIndex) => (
                      <SpotlightCard
                        key={`${activeItem.competition.id}-${spotlight.player.id ?? spotlightIndex}`}
                        item={spotlight}
                      />
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

            <div className={styles.compareFooter}>
              <div className={styles.metaText}>
                Compare the top and bottom sides before moving into the deeper league and club pages.
              </div>

              <Link to={localActionTo} className={styles.compareActionLink}>
                {activeItem.cta.label}
              </Link>
            </div>
          </div>
        </div>
      </SectionFrame>
    </div>
  );
};

interface ComparisonCardProps {
  row: LiveFootballLeagueSnapshotRow;
  variant: 'leader' | 'bottom';
  label: string;
}

const ComparisonCard: React.FC<ComparisonCardProps> = ({
  row,
  variant,
  label,
}) => {
  const cardClassName =
    variant === 'leader'
      ? `${styles.compareCard} ${styles.compareCardLeader}`
      : `${styles.compareCard} ${styles.compareCardBottom}`;

  return (
    <article className={cardClassName}>
      <div className={styles.compareHeader}>
        <div className={styles.compareHeadingGroup}>
          <div className={styles.compareLabel}>{label}</div>
          <div className={styles.compareTeamName}>
            {row.team.short_name || row.team.name}
          </div>
        </div>

        <div className={styles.comparePositionBadge}>
          #{row.position ?? '-'}
        </div>
      </div>

      <div className={styles.comparePrimaryStatRow}>
        <div className={styles.compareStatBox}>
          <span className={styles.compareStatLabel}>Points</span>
          <span className={styles.compareStatValue}>{row.points ?? '-'}</span>
        </div>

        <div className={styles.compareStatBox}>
          <span className={styles.compareStatLabel}>GD</span>
          <span className={styles.compareStatValue}>{row.goal_difference ?? '-'}</span>
        </div>

        <div className={styles.compareStatBox}>
          <span className={styles.compareStatLabel}>Played</span>
          <span className={styles.compareStatValue}>{row.played ?? '-'}</span>
        </div>
      </div>

      <div className={styles.compareSecondaryStats}>
        <span className={styles.compareSecondaryPill}>
          Record {formatRecord(row)}
        </span>

        <span className={styles.compareSecondaryPill}>
          GF {row.goals_for ?? '-'}
        </span>

        <span className={styles.compareSecondaryPill}>
          GA {row.goals_against ?? '-'}
        </span>

        <span className={styles.compareSecondaryPill}>
          Form {formatFormLabel(row.form_label)}
        </span>
      </div>
    </article>
  );
};

interface SpotlightCardProps {
  item: LiveFootballClubSpotlightPlayer;
}

const SpotlightCard: React.FC<SpotlightCardProps> = ({ item }) => {
  return (
    <article className={styles.spotlightCard}>
      <div className={styles.spotlightPlayerName}>
        {item.player.short_name || item.player.name}
      </div>

      <div className={styles.spotlightMeta}>
        {item.team_name}
        {item.player.position ? ` • ${item.player.position}` : ''}
        {item.player.shirt_number ? ` • #${item.player.shirt_number}` : ''}
      </div>

      <div className={styles.spotlightReason}>{item.reason_label}</div>

      <div className={styles.metaText}>
        {item.minutes_played !== null && item.minutes_played !== undefined
          ? `${item.minutes_played} minutes played`
          : 'Minutes not available'}
      </div>
    </article>
  );
};

export default FirstVsLastLeagueSection;