/**
 * TopScorersPanel.tsx
 *
 * Ranked list of top goal scorers for a given competition season.
 * Optionally shows a penalty-goals column.
 *
 * CSS: TopScorersPanel.module.css  (prefix: lftsp-)
 */

import React from 'react';
import type { CompetitionTopScorersResponse } from '../../types/livefootball';
import styles from './css/TopScorersPanel.module.css';

// ─── Helpers ─────────────────────────────────────────────────────────────────

type ScorerItem = CompetitionTopScorersResponse['items'][number];

const getPlayerLabel = (item: ScorerItem): string => {
  const canonicalDisplay = item.canonical_player?.display_name?.trim();
  if (canonicalDisplay) return canonicalDisplay;

  const first = item.canonical_player?.first_name?.trim() ?? '';
  const last  = item.canonical_player?.last_name?.trim()  ?? '';
  const joined = `${first} ${last}`.trim();
  if (joined) return joined;

  return item.player_name?.trim() || 'Unknown player';
};

const getTeamLabel = (item: ScorerItem): string =>
  item.team?.short_name?.trim() ||
  item.team?.tla?.trim() ||
  item.team?.name?.trim() ||
  'Unknown team';

// ─── Props ────────────────────────────────────────────────────────────────────

export interface TopScorersPanelProps {
  scorers: CompetitionTopScorersResponse | null;
  isLoading?: boolean;
  error?: string | null;
  title?: string;
  emptyMessage?: string;
  className?: string;
  maxItems?: number;
  showPenalties?: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

const TopScorersPanel: React.FC<TopScorersPanelProps> = ({
  scorers,
  isLoading = false,
  error = null,
  title = 'Top scorers',
  emptyMessage = 'No scorer data is available for this competition yet.',
  className,
  maxItems,
  showPenalties = true,
}) => {
  // ── State variants ──
  if (isLoading) {
    return (
      <section className={`${styles['lftsp-root']} ${className ?? ''}`}>
        <h2 className={styles['lftsp-title']}>{title}</h2>
        <div className={styles['lftsp-state']}>Loading scorers…</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className={`${styles['lftsp-root']} ${className ?? ''}`}>
        <h2 className={styles['lftsp-title']}>{title}</h2>
        <div className={styles['lftsp-state-error']} role="alert">{error}</div>
      </section>
    );
  }

  if (!scorers || scorers.items.length === 0) {
    return (
      <section className={`${styles['lftsp-root']} ${className ?? ''}`}>
        <h2 className={styles['lftsp-title']}>{title}</h2>
        <div className={styles['lftsp-state']}>{emptyMessage}</div>
      </section>
    );
  }

  const items =
    typeof maxItems === 'number' && maxItems > 0
      ? scorers.items.slice(0, maxItems)
      : scorers.items;

  return (
    <section className={`${styles['lftsp-root']} ${className ?? ''}`}>
      {/* Panel header */}
      <div className={styles['lftsp-panel-header']}>
        <h2 className={styles['lftsp-title']}>{title}</h2>
        <p className={styles['lftsp-competition-meta']}>
          {scorers.competition.name}
          {scorers.competition.area_name ? ` · ${scorers.competition.area_name}` : ''}
          {scorers.season_label ? ` · ${scorers.season_label}` : ''}
        </p>
      </div>

      {/* Scorer rows */}
      <div className={styles['lftsp-list']}>
        {items.map((item, idx) => {
          const playerLabel = getPlayerLabel(item);
          const teamLabel   = getTeamLabel(item);
          const isRawDifferent =
            item.player_name?.trim() && item.player_name.trim() !== playerLabel;
          const rankKey = `${item.rank}-${item.external_player_id ?? item.canonical_player?.id ?? item.player_name}`;

          return (
            <div
              key={rankKey}
              className={`${styles['lftsp-row']} ${idx === 0 ? styles['lftsp-row--first'] : ''}`}
            >
              {/* Rank badge */}
              <span className={`${styles['lftsp-rank']} ${idx === 0 ? styles['lftsp-rank--first'] : ''}`}>
                {item.rank}
              </span>

              {/* Player info */}
              <div className={styles['lftsp-player-info']}>
                <span className={styles['lftsp-player-name']}>{playerLabel}</span>
                {isRawDifferent && (
                  <span className={styles['lftsp-player-raw']}>{item.player_name}</span>
                )}
              </div>

              {/* Team */}
              <span className={styles['lftsp-team']}>{teamLabel}</span>

              {/* Goals */}
              <span className={styles['lftsp-goals']}>{item.goals}</span>

              {/* Penalties */}
              {showPenalties && (
                <span className={styles['lftsp-pens']}>{item.penalties ?? '—'}</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Column labels footer */}
      <div className={styles['lftsp-col-labels']}>
        <span />
        <span>Player</span>
        <span>Club</span>
        <span>G</span>
        {showPenalties && <span>Pen</span>}
      </div>
    </section>
  );
};

export default TopScorersPanel;