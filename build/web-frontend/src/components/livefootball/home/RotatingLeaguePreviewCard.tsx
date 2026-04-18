import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import type { LiveFootballLeagueSnapshotCard } from '../../../types/livefootball';
import { buildLiveFootballLink } from './linking';
import SectionFrame from './SectionFrame';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

interface Props {
  cards: LiveFootballLeagueSnapshotCard[];
}

const AUTO_ROTATE_MS = 5000;

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

const RotatingLeaguePreviewCard: React.FC<Props> = ({ cards }) => {
  const [index, setIndex] = useState(0);
  const [timerResetKey, setTimerResetKey] = useState(0);
  const pausedRef = useRef(false);

  useEffect(() => {
    if (index > cards.length - 1) {
      setIndex(0);
    }
  }, [cards, index]);

  useEffect(() => {
    if (cards.length <= 1) {
      return;
    }

    const interval = window.setInterval(() => {
      if (!pausedRef.current) {
        setIndex((current) => (current + 1) % cards.length);
      }
    }, AUTO_ROTATE_MS);

    return () => window.clearInterval(interval);
  }, [cards, timerResetKey]);

  if (cards.length === 0) {
    return null;
  }

  const activeCard = cards[index];
  const syncedAtLabel = formatSyncedAt(activeCard.synced_at);
  const actionTo = buildLiveFootballLink(activeCard.cta.path, activeCard.cta.query);

  const resetRotationTimer = (): void => {
    setTimerResetKey((current) => current + 1);
  };

  const handlePrev = (): void => {
    setIndex((current) => (current - 1 + cards.length) % cards.length);
    resetRotationTimer();
  };

  const handleNext = (): void => {
    setIndex((current) => (current + 1) % cards.length);
    resetRotationTimer();
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
        title="League snapshot"
        subtitle="Top and bottom table previews from the current synced standings."
        actionLabel={activeCard.cta.label}
        actionTo={actionTo}
        meta={
          <span className={styles.metaText}>
            {cards.length > 1
              ? `League ${index + 1} of ${cards.length}`
              : 'Single league preview'}
            {syncedAtLabel ? ` • Updated ${syncedAtLabel}` : ''}
          </span>
        }
      >
        <div className={styles.carouselShell}>
          <div className={styles.carouselBody}>
            <div key={`${activeCard.competition.id ?? activeCard.competition.code ?? index}-${index}`} className={styles.carouselStage}>
              <div className={styles.rowSplit}>
                <div>
                  <h3 className={styles.compactTitle}>{activeCard.competition.name}</h3>

                  <div className={styles.carouselLeagueMeta}>
                    <span className={styles.activeLeaguePill}>Now viewing</span>
                    <span className={styles.metaText}>
                      {activeCard.competition.country || activeCard.competition.code || 'League overview'}
                    </span>
                  </div>
                </div>

                {cards.length > 1 ? (
                  <div className={styles.carouselControls}>
                    <button
                      type="button"
                      aria-label="Previous league"
                      className={`${styles.carouselButton} ${styles.carouselButtonStrong}`}
                      onClick={handlePrev}
                    >
                      ‹
                    </button>

                    <span className={styles.carouselIndex}>
                      {index + 1}/{cards.length}
                    </span>

                    <button
                      type="button"
                      aria-label="Next league"
                      className={`${styles.carouselButton} ${styles.carouselButtonStrong}`}
                      onClick={handleNext}
                    >
                      ›
                    </button>
                  </div>
                ) : null}
              </div>

              <div className={styles.snapshotColumns}>
                <div className={styles.snapshotColumn}>
                  <div className={styles.inlinePill}>Top 3</div>

                  {activeCard.top_rows.length === 0 ? (
                    <div className={styles.emptyState}>No top-row preview available.</div>
                  ) : (
                    <div className={styles.snapshotList}>
                      {activeCard.top_rows.map((row) => (
                        <div
                          key={`top-${row.team.id ?? row.team.name}-${row.position ?? 'na'}`}
                          className={styles.snapshotRow}
                        >
                          <div className={styles.snapshotPosition}>#{row.position ?? '-'}</div>

                          <div className={styles.snapshotTeam}>
                            <div className={styles.snapshotTeamName}>
                              {row.team.short_name || row.team.name}
                            </div>
                            <div className={styles.snapshotMeta}>
                              GD {row.goal_difference ?? '-'} • P {row.played ?? '-'}
                            </div>
                          </div>

                          <div className={styles.snapshotPoints}>{row.points ?? '-'}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className={styles.snapshotColumn}>
                  <div className={styles.inlinePill}>Bottom 3</div>

                  {activeCard.bottom_rows.length === 0 ? (
                    <div className={styles.emptyState}>No bottom-row preview available.</div>
                  ) : (
                    <div className={styles.snapshotList}>
                      {activeCard.bottom_rows.map((row) => (
                        <div
                          key={`bottom-${row.team.id ?? row.team.name}-${row.position ?? 'na'}`}
                          className={styles.snapshotRow}
                        >
                          <div className={styles.snapshotPosition}>#{row.position ?? '-'}</div>

                          <div className={styles.snapshotTeam}>
                            <div className={styles.snapshotTeamName}>
                              {row.team.short_name || row.team.name}
                            </div>
                            <div className={styles.snapshotMeta}>
                              GD {row.goal_difference ?? '-'} • P {row.played ?? '-'}
                            </div>
                          </div>

                          <div className={styles.snapshotPoints}>{row.points ?? '-'}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className={styles.rowSplit}>
                <div className={styles.carouselHintText}>
                  Auto-rotates every 5 seconds. Hover pauses. Manual navigation resets the timer.
                </div>

                <Link to={actionTo} className={styles.actionButton}>
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