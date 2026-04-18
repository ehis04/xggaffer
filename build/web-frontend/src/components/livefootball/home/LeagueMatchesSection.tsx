import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { LiveFootballLeagueMatchPreview } from '../../../types/livefootball';
import SectionFrame from './SectionFrame';
import { buildLiveFootballLink } from './linking';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

interface LeagueMatchesSectionProps {
  title: string;
  subtitle?: string;
  actionLabel?: string;
  actionTo?: string;
  groups: LiveFootballLeagueMatchPreview[];
  tab: 'recent' | 'upcoming';
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

const formatKickoff = (value?: string | null): string | null => {
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

const normaliseStatusLabel = (value?: string | null): string => {
  const raw = (value || '').trim();
  if (!raw) {
    return 'Unknown';
  }

  return raw
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
};

const isFinishedStatus = (value?: string | null): boolean => {
  const raw = (value || '').toUpperCase();
  return ['FINISHED', 'AWARDED', 'AFTER_EXTRA_TIME', 'PENALTY_SHOOTOUT'].includes(raw);
};

const LeagueMatchesSection: React.FC<LeagueMatchesSectionProps> = ({
  title,
  subtitle,
  actionLabel,
  actionTo,
  groups,
  tab,
  emptyMessage,
}) => {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (index > groups.length - 1) {
      setIndex(0);
    }
  }, [groups, index]);

  if (groups.length === 0) {
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

  const activeGroup = groups[index];
  const syncedAtLabel = formatSyncedAt(activeGroup.synced_at);
  const groupActionTo = buildLiveFootballLink(activeGroup.cta.path, activeGroup.cta.query);

  const handlePrev = (): void => {
    setIndex((current) => (current - 1 + groups.length) % groups.length);
  };

  const handleNext = (): void => {
    setIndex((current) => (current + 1) % groups.length);
  };

  return (
    <SectionFrame
      title={title}
      subtitle={subtitle}
      actionLabel={actionLabel}
      actionTo={actionTo}
      meta={
        <span className={styles.metaText}>
          League {index + 1} of {groups.length}
        </span>
      }
    >
      <div className={styles.carouselShell}>
        <div className={styles.carouselBody}>
          <div className={styles.matchLeagueSummary}>
            <div className={styles.matchLeagueTitleBlock}>
              <div className={styles.matchLeagueName}>
                {activeGroup.competition.name}
              </div>

              <div className={styles.matchLeagueMeta}>
                {activeGroup.competition.country || activeGroup.competition.code || 'League preview'}
                {syncedAtLabel ? ` • Updated ${syncedAtLabel}` : ''}
              </div>
            </div>

            <div className={styles.carouselControls}>
              <button
                type="button"
                aria-label={`Previous ${tab} league`}
                className={styles.carouselButton}
                onClick={handlePrev}
                disabled={groups.length <= 1}
              >
                ‹
              </button>

              <span className={styles.carouselIndex}>
                {index + 1}/{groups.length}
              </span>

              <button
                type="button"
                aria-label={`Next ${tab} league`}
                className={styles.carouselButton}
                onClick={handleNext}
                disabled={groups.length <= 1}
              >
                ›
              </button>
            </div>
          </div>

          {activeGroup.items.length === 0 ? (
            <div className={styles.emptyState}>
              No {tab} matches available for this league right now.
            </div>
          ) : (
            <div className={styles.matchList}>
              {activeGroup.items.map((match, matchIndex) => {
                const kickoffLabel = formatKickoff(match.utc_date);
                const fixtureLabel = `${match.home_team.name} vs ${match.away_team.name}`;
                const statusLabel = normaliseStatusLabel(match.status);
                const finished = isFinishedStatus(match.status);

                return (
                  <article
                    key={`${activeGroup.competition.id}-${match.id ?? matchIndex}`}
                    className={styles.matchCard}
                  >
                    <div className={styles.matchTopRow}>
                      <div className={styles.matchTeams}>
                        <div className={styles.matchFixture}>{fixtureLabel}</div>
                        <div className={styles.matchVenue}>
                          {match.venue_label || 'Fixture preview'}
                        </div>
                      </div>

                      <span
                        className={`${styles.matchStatusPill} ${
                          finished ? styles.matchStatusFinished : styles.matchStatusUpcoming
                        }`}
                      >
                        {statusLabel}
                      </span>
                    </div>

                    <div className={styles.matchBottomRow}>
                      <div className={styles.matchMeta}>
                        {kickoffLabel ? (
                          <span className={styles.matchMetaPill}>{kickoffLabel}</span>
                        ) : null}

                      </div>

                      <div className={finished && match.score_line ? styles.matchScore : styles.matchDateText}>
                        {finished && match.score_line ? match.score_line : kickoffLabel || 'Kick-off TBC'}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}

          <div className={styles.matchSectionFooter}>
            <div className={styles.metaText}>
              {tab === 'recent'
                ? 'Latest completed fixtures preview.'
                : 'Next scheduled fixtures preview.'}
            </div>

            <Link to={groupActionTo} className={styles.matchLeagueAction}>
              {activeGroup.cta.label}
            </Link>
          </div>
        </div>
      </div>
    </SectionFrame>
  );
};

export default LeagueMatchesSection;