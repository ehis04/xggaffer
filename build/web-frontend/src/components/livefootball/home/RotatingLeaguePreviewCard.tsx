/**
 * RotatingLeaguePreviewCard.tsx
 *
 * Auto-rotating carousel that shows the top-3 and bottom-3 standings
 * snapshot for each tracked competition. Pauses on hover and resets the
 * rotation timer on manual navigation.
 *
 * CSS: LiveFootballBasePage.module.css  (prefix: lfb-)
 */

import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import type { LiveFootballLeagueSnapshotCard } from '../../../types/livefootball';
import { buildLiveFootballLink } from './linking';
import SectionFrame from './SectionFrame';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

// ─── Constants ────────────────────────────────────────────────────────────────

const AUTO_ROTATE_MS = 5000;

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatSyncedAt = (value?: string | null): string | null => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
};

// ─── Props ────────────────────────────────────────────────────────────────────

interface Props {
  cards: LiveFootballLeagueSnapshotCard[];
}

// ─── Component ────────────────────────────────────────────────────────────────

const RotatingLeaguePreviewCard: React.FC<Props> = ({ cards }) => {
  const [index, setIndex]               = useState(0);
  const [timerResetKey, setTimerResetKey] = useState(0);
  const pausedRef                        = useRef(false);

  useEffect(() => {
    if (index > cards.length - 1) setIndex(0);
  }, [cards, index]);

  useEffect(() => {
    if (cards.length <= 1) return;
    const interval = window.setInterval(() => {
      if (!pausedRef.current) setIndex((c) => (c + 1) % cards.length);
    }, AUTO_ROTATE_MS);
    return () => window.clearInterval(interval);
  }, [cards, timerResetKey]);

  if (cards.length === 0) return null;

  const activeCard   = cards[index];
  const syncedAtLabel = formatSyncedAt(activeCard.synced_at);
  const actionTo     = buildLiveFootballLink(activeCard.cta.path, activeCard.cta.query);

  const resetTimer = () => setTimerResetKey((k) => k + 1);
  const handlePrev = () => { setIndex((c) => (c - 1 + cards.length) % cards.length); resetTimer(); };
  const handleNext = () => { setIndex((c) => (c + 1) % cards.length); resetTimer(); };

  return (
    <div
      onMouseEnter={() => { pausedRef.current = true; }}
      onMouseLeave={() => { pausedRef.current = false; }}
    >
      <SectionFrame
        title="League snapshot"
        subtitle="Top and bottom table previews from the current synced standings."
        actionLabel={activeCard.cta.label}
        actionTo={actionTo}
        meta={
          <span className={styles['lfb-meta-text']}>
            {cards.length > 1
              ? `League ${index + 1} of ${cards.length}`
              : 'Single league preview'}
            {syncedAtLabel ? ` • Updated ${syncedAtLabel}` : ''}
          </span>
        }
      >
        <div className={styles['lfb-carousel-shell']}>
          <div className={styles['lfb-carousel-body']}>
            <div
              key={`${activeCard.competition.id ?? activeCard.competition.code ?? index}-${index}`}
              className={styles['lfb-carousel-stage']}
            >
              {/* League name + controls */}
              <div className={styles['lfb-row-split']}>
                <div>
                  <h3 className={styles['lfb-compact-title']}>{activeCard.competition.name}</h3>
                  <div className={styles['lfb-carousel-league-meta']}>
                    <span className={styles['lfb-active-league-pill']}>Now viewing</span>
                    <span className={styles['lfb-meta-text']}>
                      {activeCard.competition.country || activeCard.competition.code || 'League overview'}
                    </span>
                  </div>
                </div>

                {cards.length > 1 && (
                  <div className={styles['lfb-carousel-controls']}>
                    <button
                      type="button"
                      aria-label="Previous league"
                      className={`${styles['lfb-carousel-btn']} ${styles['lfb-carousel-btn-strong']}`}
                      onClick={handlePrev}
                    >
                      ‹
                    </button>
                    <span className={styles['lfb-carousel-index']}>
                      {index + 1}/{cards.length}
                    </span>
                    <button
                      type="button"
                      aria-label="Next league"
                      className={`${styles['lfb-carousel-btn']} ${styles['lfb-carousel-btn-strong']}`}
                      onClick={handleNext}
                    >
                      ›
                    </button>
                  </div>
                )}
              </div>

              {/* Top / bottom columns */}
              <div className={styles['lfb-snapshot-columns']}>
                {/* Top 3 */}
                <div className={styles['lfb-snapshot-column']}>
                  <div className={styles['lfb-inline-pill']}>Top 3</div>
                  {activeCard.top_rows.length === 0 ? (
                    <div className={styles['lfb-empty-state']}>No top-row preview available.</div>
                  ) : (
                    <div className={styles['lfb-snapshot-list']}>
                      {activeCard.top_rows.map((row) => (
                        <div
                          key={`top-${row.team.id ?? row.team.name}-${row.position ?? 'na'}`}
                          className={styles['lfb-snapshot-row']}
                        >
                          <div className={styles['lfb-snapshot-position']}>#{row.position ?? '-'}</div>
                          <div className={styles['lfb-snapshot-team']}>
                            <div className={styles['lfb-snapshot-team-name']}>
                              {row.team.short_name || row.team.name}
                            </div>
                            <div className={styles['lfb-snapshot-meta']}>
                              GD {row.goal_difference ?? '-'} • P {row.played ?? '-'}
                            </div>
                          </div>
                          <div className={styles['lfb-snapshot-points']}>{row.points ?? '-'}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Bottom 3 */}
                <div className={styles['lfb-snapshot-column']}>
                  <div className={styles['lfb-inline-pill']}>Bottom 3</div>
                  {activeCard.bottom_rows.length === 0 ? (
                    <div className={styles['lfb-empty-state']}>No bottom-row preview available.</div>
                  ) : (
                    <div className={styles['lfb-snapshot-list']}>
                      {activeCard.bottom_rows.map((row) => (
                        <div
                          key={`bottom-${row.team.id ?? row.team.name}-${row.position ?? 'na'}`}
                          className={styles['lfb-snapshot-row']}
                        >
                          <div className={styles['lfb-snapshot-position']}>#{row.position ?? '-'}</div>
                          <div className={styles['lfb-snapshot-team']}>
                            <div className={styles['lfb-snapshot-team-name']}>
                              {row.team.short_name || row.team.name}
                            </div>
                            <div className={styles['lfb-snapshot-meta']}>
                              GD {row.goal_difference ?? '-'} • P {row.played ?? '-'}
                            </div>
                          </div>
                          <div className={styles['lfb-snapshot-points']}>{row.points ?? '-'}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Footer */}
              <div className={styles['lfb-row-split']}>
                <div className={styles['lfb-carousel-hint-text']}>
                  Auto-rotates every 5 seconds. Hover pauses. Manual navigation resets the timer.
                </div>
                <Link to={actionTo} className={styles['lfb-action-btn']}>
                  {activeCard.cta.label}
                </Link>
              </div>
            </div>
          </div>
        </div>
      </SectionFrame>
    </div>
  );
};

export default RotatingLeaguePreviewCard;