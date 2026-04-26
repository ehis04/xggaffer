/**
 * FirstVsLastLeagueSection.tsx
 *
 * Auto-rotating carousel comparing the league leader and bottom club
 * for each tracked competition, with spotlight player cards below.
 * Pauses on hover.
 *
 * CSS: LiveFootballBasePage.module.css  (prefix: lfb-)
 */

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

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatSyncedAt = (value?: string | null): string | null => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
};

const formatFormLabel = (value?: string | null): string => (value || '').trim() || 'No form data';

const formatRecord = (row: LiveFootballLeagueSnapshotRow): string =>
  `${row.won ?? '-'}-${row.drawn ?? '-'}-${row.lost ?? '-'}`;

// ─── ComparisonCard sub-component ────────────────────────────────────────────

interface ComparisonCardProps {
  row: LiveFootballLeagueSnapshotRow;
  variant: 'leader' | 'bottom';
  label: string;
}

const ComparisonCard: React.FC<ComparisonCardProps> = ({ row, variant, label }) => (
  <article
    className={`${styles['lfb-compare-card']} ${
      variant === 'leader' ? styles['lfb-compare-card-leader'] : styles['lfb-compare-card-bottom']
    }`}
  >
    <div className={styles['lfb-compare-header']}>
      <div className={styles['lfb-compare-heading-group']}>
        <div className={styles['lfb-compare-label']}>{label}</div>
        <div className={styles['lfb-compare-team-name']}>
          {row.team.short_name || row.team.name}
        </div>
      </div>
      <div className={styles['lfb-compare-position-badge']}>#{row.position ?? '-'}</div>
    </div>

    <div className={styles['lfb-compare-primary-stat-row']}>
      <div className={styles['lfb-compare-stat-box']}>
        <span className={styles['lfb-compare-stat-label']}>Points</span>
        <span className={styles['lfb-compare-stat-value']}>{row.points ?? '-'}</span>
      </div>
      <div className={styles['lfb-compare-stat-box']}>
        <span className={styles['lfb-compare-stat-label']}>GD</span>
        <span className={styles['lfb-compare-stat-value']}>{row.goal_difference ?? '-'}</span>
      </div>
      <div className={styles['lfb-compare-stat-box']}>
        <span className={styles['lfb-compare-stat-label']}>Played</span>
        <span className={styles['lfb-compare-stat-value']}>{row.played ?? '-'}</span>
      </div>
    </div>

    <div className={styles['lfb-compare-secondary-stats']}>
      <span className={styles['lfb-compare-secondary-pill']}>Record {formatRecord(row)}</span>
      <span className={styles['lfb-compare-secondary-pill']}>GF {row.goals_for ?? '-'}</span>
      <span className={styles['lfb-compare-secondary-pill']}>GA {row.goals_against ?? '-'}</span>
      <span className={styles['lfb-compare-secondary-pill']}>Form {formatFormLabel(row.form_label)}</span>
    </div>
  </article>
);

// ─── SpotlightCard sub-component ─────────────────────────────────────────────

interface SpotlightCardProps {
  item: LiveFootballClubSpotlightPlayer;
}

const SpotlightCard: React.FC<SpotlightCardProps> = ({ item }) => (
  <article className={styles['lfb-spotlight-card']}>
    <div className={styles['lfb-spotlight-player-name']}>
      {item.player.short_name || item.player.name}
    </div>
    <div className={styles['lfb-spotlight-meta']}>
      {item.team_name}
      {item.player.position ? ` • ${item.player.position}` : ''}
      {item.player.shirt_number ? ` • #${item.player.shirt_number}` : ''}
    </div>
    <div className={styles['lfb-spotlight-reason']}>{item.reason_label}</div>
    <div className={styles['lfb-meta-text']}>
      {item.minutes_played !== null && item.minutes_played !== undefined
        ? `${item.minutes_played} minutes played`
        : 'Minutes not available'}
    </div>
  </article>
);

// ─── Props ────────────────────────────────────────────────────────────────────

interface FirstVsLastLeagueSectionProps {
  title: string;
  subtitle?: string;
  actionLabel?: string;
  actionTo?: string;
  items: LiveFootballFirstVsLastLeagueCard[];
  emptyMessage: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

const FirstVsLastLeagueSection: React.FC<FirstVsLastLeagueSectionProps> = ({
  title,
  subtitle,
  actionLabel,
  actionTo,
  items,
  emptyMessage,
}) => {
  const [index, setIndex]   = useState(0);
  const pausedRef           = useRef(false);

  useEffect(() => {
    if (index > items.length - 1) setIndex(0);
  }, [items, index]);

  useEffect(() => {
    if (items.length <= 1) return;
    const interval = window.setInterval(() => {
      if (!pausedRef.current) setIndex((c) => (c + 1) % items.length);
    }, 5000);
    return () => window.clearInterval(interval);
  }, [items]);

  if (items.length === 0) {
    return (
      <SectionFrame title={title} subtitle={subtitle} actionLabel={actionLabel} actionTo={actionTo}>
        <div className={styles['lfb-empty-state']}>{emptyMessage}</div>
      </SectionFrame>
    );
  }

  const activeItem     = items[index];
  const syncedAtLabel  = formatSyncedAt(activeItem.synced_at);
  const localActionTo  = buildLiveFootballLink(activeItem.cta.path, activeItem.cta.query);

  const handlePrev = () => setIndex((c) => (c - 1 + items.length) % items.length);
  const handleNext = () => setIndex((c) => (c + 1) % items.length);

  return (
    <div
      onMouseEnter={() => { pausedRef.current = true; }}
      onMouseLeave={() => { pausedRef.current = false; }}
    >
      <SectionFrame
        title={title}
        subtitle={subtitle}
        actionLabel={actionLabel}
        actionTo={actionTo}
        meta={
          <span className={styles['lfb-meta-text']}>
            League {index + 1} of {items.length}
          </span>
        }
      >
        <div className={styles['lfb-carousel-shell']}>
          <div className={styles['lfb-carousel-body']}>

            {/* League header + controls */}
            <div className={styles['lfb-match-league-summary']}>
              <div className={styles['lfb-match-league-title-block']}>
                <div className={styles['lfb-match-league-name']}>{activeItem.competition.name}</div>
                <div className={styles['lfb-match-league-meta']}>
                  {activeItem.competition.country || activeItem.competition.code || 'League comparison'}
                  {syncedAtLabel ? ` • Updated ${syncedAtLabel}` : ''}
                </div>
              </div>

              <div className={styles['lfb-carousel-controls']}>
                <button
                  type="button"
                  aria-label="Previous first-v-last league"
                  className={styles['lfb-carousel-btn']}
                  onClick={handlePrev}
                  disabled={items.length <= 1}
                >
                  ‹
                </button>
                <span className={styles['lfb-carousel-index']}>{index + 1}/{items.length}</span>
                <button
                  type="button"
                  aria-label="Next first-v-last league"
                  className={styles['lfb-carousel-btn']}
                  onClick={handleNext}
                  disabled={items.length <= 1}
                >
                  ›
                </button>
              </div>
            </div>

            {!activeItem.leader || !activeItem.bottom ? (
              <div className={styles['lfb-empty-state']}>
                No first-versus-last comparison is available for this league right now.
              </div>
            ) : (
              <>
                <div className={styles['lfb-compare-grid']}>
                  <ComparisonCard row={activeItem.leader} variant="leader" label="League leader" />
                  <ComparisonCard row={activeItem.bottom} variant="bottom" label="Bottom club" />
                </div>

                <div className={styles['lfb-spotlight-section']}>
                  <div className={styles['lfb-row-split']}>
                    <div className={styles['lfb-compact-title']}>Spotlight players</div>
                    <div className={styles['lfb-meta-text']}>
                      Quick player context from the leading and trailing sides.
                    </div>
                  </div>

                  {activeItem.spotlight_players.length === 0 ? (
                    <div className={styles['lfb-empty-state']}>
                      No spotlight players are available for this league right now.
                    </div>
                  ) : (
                    <div className={styles['lfb-spotlight-grid']}>
                      {activeItem.spotlight_players.map((spotlight, spotlightIdx) => (
                        <SpotlightCard
                          key={`${activeItem.competition.id}-${spotlight.player.id ?? spotlightIdx}`}
                          item={spotlight}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Footer */}
            <div className={styles['lfb-compare-footer']}>
              <div className={styles['lfb-meta-text']}>
                Compare the top and bottom sides before moving into the deeper league and club pages.
              </div>
              <Link to={localActionTo} className={styles['lfb-compare-action-link']}>
                {activeItem.cta.label}
              </Link>
            </div>

          </div>
        </div>
      </SectionFrame>
    </div>
  );
};

export default FirstVsLastLeagueSection;