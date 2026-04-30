/**
 * LeagueMatchesSection.tsx
 *
 * Carousel of recent or upcoming match cards grouped by competition.
 * One group visible at a time; prev/next controls cycle through leagues.
 *
 * CSS: LiveFootballBasePage.module.css  (prefix: lfb-)
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { LiveFootballLeagueMatchPreview } from '../../../types/livefootball';
import SectionFrame from './SectionFrame';
import { buildLiveFootballLink } from './linking';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatSyncedAt = (value?: string | null): string | null => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
};

const formatKickoff = (value?: string | null): string | null => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
};

const normaliseStatusLabel = (value?: string | null): string => {
  const raw = (value || '').trim();
  if (!raw) return 'Unknown';
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

// ─── Props ────────────────────────────────────────────────────────────────────

interface LeagueMatchesSectionProps {
  title: string;
  subtitle?: string;
  actionLabel?: string;
  actionTo?: string;
  groups: LiveFootballLeagueMatchPreview[];
  tab: 'recent' | 'upcoming';
  emptyMessage: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

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
    if (index > groups.length - 1) setIndex(0);
  }, [groups, index]);

  if (groups.length === 0) {
    return (
      <SectionFrame title={title} subtitle={subtitle} actionLabel={actionLabel} actionTo={actionTo}>
        <div className={styles['lfb-empty-state']}>{emptyMessage}</div>
      </SectionFrame>
    );
  }

  const activeGroup    = groups[index];
  const syncedAtLabel  = formatSyncedAt(activeGroup.synced_at);
  const groupActionTo  = buildLiveFootballLink(activeGroup.cta.path, activeGroup.cta.query);

  const handlePrev = () => setIndex((c) => (c - 1 + groups.length) % groups.length);
  const handleNext = () => setIndex((c) => (c + 1) % groups.length);

  return (
    <SectionFrame
      title={title}
      subtitle={subtitle}
      actionLabel={actionLabel}
      actionTo={actionTo}
      meta={
        <span className={styles['lfb-meta-text']}>League {index + 1} of {groups.length}</span>
      }
    >
      <div className={styles['lfb-carousel-shell']}>
        <div className={styles['lfb-carousel-body']}>

          {/* League header + controls */}
          <div className={styles['lfb-match-league-summary']}>
            <div className={styles['lfb-match-league-title-block']}>
              <div className={styles['lfb-match-league-name']}>{activeGroup.competition.name}</div>
              <div className={styles['lfb-match-league-meta']}>
                {activeGroup.competition.country || activeGroup.competition.code || 'League preview'}
                {syncedAtLabel ? ` • Updated ${syncedAtLabel}` : ''}
              </div>
            </div>

            <div className={styles['lfb-carousel-controls']}>
              <button
                type="button"
                aria-label={`Previous ${tab} league`}
                className={styles['lfb-carousel-btn']}
                onClick={handlePrev}
                disabled={groups.length <= 1}
              >
                ‹
              </button>
              <span className={styles['lfb-carousel-index']}>{index + 1}/{groups.length}</span>
              <button
                type="button"
                aria-label={`Next ${tab} league`}
                className={styles['lfb-carousel-btn']}
                onClick={handleNext}
                disabled={groups.length <= 1}
              >
                ›
              </button>
            </div>
          </div>

          {/* Match list */}
          {activeGroup.items.length === 0 ? (
            <div className={styles['lfb-empty-state']}>
              No {tab} matches available for this league right now.
            </div>
          ) : (
            <div className={styles['lfb-match-list']}>
              {activeGroup.items.map((match, matchIndex) => {
                const kickoffLabel = formatKickoff(match.utc_date);
                const fixtureLabel = `${match.home_team.name} vs ${match.away_team.name}`;
                const statusLabel  = normaliseStatusLabel(match.status);
                const finished     = isFinishedStatus(match.status);

                return (
                  <article
                    key={`${activeGroup.competition.id}-${match.id ?? matchIndex}`}
                    className={styles['lfb-match-card']}
                  >
                    <div className={styles['lfb-match-top-row']}>
                      <div className={styles['lfb-match-teams']}>
                        <div className={styles['lfb-match-fixture']}>{fixtureLabel}</div>
                        <div className={styles['lfb-match-venue']}>
                          {match.venue_label || 'Fixture preview'}
                        </div>
                      </div>
                      <span
                        className={`${styles['lfb-match-status-pill']} ${
                          finished
                            ? styles['lfb-match-status-finished']
                            : styles['lfb-match-status-upcoming']
                        }`}
                      >
                        {statusLabel}
                      </span>
                    </div>

                    <div className={styles['lfb-match-bottom-row']}>
                      <div className={styles['lfb-match-meta']}>
                        {kickoffLabel && (
                          <span className={styles['lfb-match-meta-pill']}>{kickoffLabel}</span>
                        )}
                      </div>
                      <div
                        className={
                          finished && match.score_line
                            ? styles['lfb-match-score']
                            : styles['lfb-match-date-text']
                        }
                      >
                        {finished && match.score_line
                          ? match.score_line
                          : kickoffLabel || 'Kick-off TBC'}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}

          {/* Footer */}
          <div className={styles['lfb-match-section-footer']}>
            <div className={styles['lfb-meta-text']}>
              {tab === 'recent'
                ? 'Latest completed fixtures preview.'
                : 'Next scheduled fixtures preview.'}
            </div>
            <Link to={groupActionTo} className={styles['lfb-match-league-action']}>
              {activeGroup.cta.label}
            </Link>
          </div>

        </div>
      </div>
    </SectionFrame>
  );
};

export default LeagueMatchesSection;