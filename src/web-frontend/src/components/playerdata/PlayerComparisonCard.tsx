import React from 'react';
import type {
  PlayerComparisonMetric,
  PlayerComparisonResult,
} from '../../types/playerdata';
import styles from './PlayerComparisonCard.module.css';

interface PlayerComparisonCardProps {
  comparison?: PlayerComparisonResult | null;
  isLoading?: boolean;
  error?: string | null;
  title?: string;
  emptyMessage?: string;
  maxMetrics?: number;
  className?: string;
}

const DEFAULT_EMPTY_MESSAGE =
  'No deterministic player comparison is available for the selected filters.';

const formatDateTime = (value?: string | null): string | null => {
  if (!value) return null;

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;

  return date.toLocaleString('en-IE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getInitials = (name?: string | null): string => {
  if (!name) return '?';

  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '?';

  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
};

const getPlayerDisplayName = (
  player?: PlayerComparisonResult['player_a']['player'] | null,
): string => {
  return (
    player?.display_name ||
    player?.full_name ||
    player?.short_name ||
    'Unknown player'
  );
};

const renderValue = (value?: string | number | null): string => {
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
};

const getVisibleMetrics = (
  metrics?: PlayerComparisonMetric[],
  maxMetrics: number = 8,
): PlayerComparisonMetric[] => {
  if (!metrics?.length) return [];

  return metrics
    .filter(
      (metric) =>
        metric.player_a_formatted !== null ||
        metric.player_b_formatted !== null ||
        metric.player_a_value !== null ||
        metric.player_b_value !== null,
    )
    .slice(0, maxMetrics);
};

const PlayerComparisonCard: React.FC<PlayerComparisonCardProps> = ({
  comparison,
  isLoading = false,
  error = null,
  title = 'Player comparison',
  emptyMessage = DEFAULT_EMPTY_MESSAGE,
  maxMetrics = 8,
  className,
}) => {
  if (isLoading) {
    return (
      <section className={`${styles.card} ${className ?? ''}`.trim()}>
        <div className={styles.loadingState}>Loading player comparison…</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className={`${styles.card} ${className ?? ''}`.trim()}>
        <div className={styles.errorState}>{error}</div>
      </section>
    );
  }

  if (!comparison || comparison.has_comparison_data === false) {
    return (
      <section className={`${styles.card} ${className ?? ''}`.trim()}>
        <div className={styles.emptyState}>
          <h3 className={styles.sectionTitle}>{title}</h3>
          <p className={styles.emptyMessage}>{emptyMessage}</p>

          {!!comparison?.missing_reasons?.length && (
            <ul className={styles.reasonList}>
              {comparison.missing_reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
        </div>
      </section>
    );
  }

  const playerAName = getPlayerDisplayName(comparison.player_a.player);
  const playerBName = getPlayerDisplayName(comparison.player_b.player);
  const metrics = getVisibleMetrics(comparison.metrics, maxMetrics);
  const explanation = comparison.explanation;
  const providerCoverage = comparison.provider_coverage;

  const freshnessText =
    providerCoverage?.freshness_label ||
    formatDateTime(providerCoverage?.last_synced_at);

  const overallWinner = comparison.overall_winner;
  const overallWinnerIsTie = overallWinner?.winner === 'tie';
  const overallWinnerIsA =
    overallWinner?.winner_player_id === comparison.player_a.player.id;
  const overallWinnerIsB =
    overallWinner?.winner_player_id === comparison.player_b.player.id;

  return (
    <section className={`${styles.card} ${className ?? ''}`.trim()}>
      <div className={styles.topBar}>
        <div>
          <p className={styles.eyebrow}>{title}</p>
          <h3 className={styles.pageTitle}>Deterministic comparison</h3>
        </div>

        <div className={styles.contextBadges}>
          {comparison.context?.season && (
            <span className={styles.badge}>{comparison.context.season}</span>
          )}
          {comparison.context?.competition_name && (
            <span className={styles.badge}>
              {comparison.context.competition_name}
            </span>
          )}
          {comparison.context?.provider && (
            <span className={styles.badgeMuted}>{comparison.context.provider}</span>
          )}
        </div>
      </div>

      <div className={styles.playersGrid}>
        <div
          className={`${styles.playerPanel} ${overallWinnerIsA ? styles.playerPanelWinner : ''}`.trim()}
        >
          <div className={styles.playerIdentity}>
            {comparison.player_a.player.photo_url ? (
              <img
                src={comparison.player_a.player.photo_url}
                alt={playerAName}
                className={styles.avatar}
              />
            ) : (
              <div className={styles.avatarFallback} aria-hidden="true">
                {getInitials(playerAName)}
              </div>
            )}

            <div className={styles.playerText}>
              <p className={styles.playerSideLabel}>Player A</p>
              <h4 className={styles.playerName}>{playerAName}</h4>

              <div className={styles.playerMeta}>
                {comparison.player_a.club?.name && (
                  <span className={styles.playerMetaItem}>
                    {comparison.player_a.club.name}
                  </span>
                )}
                {comparison.player_a.player.position && (
                  <span className={styles.playerMetaItem}>
                    {comparison.player_a.player.position}
                  </span>
                )}
                {comparison.player_a.player.age !== null &&
                  comparison.player_a.player.age !== undefined && (
                    <span className={styles.playerMetaItem}>
                      {comparison.player_a.player.age} yrs
                    </span>
                  )}
              </div>
            </div>
          </div>

          {overallWinnerIsA && (
            <span className={styles.overallWinnerBadge}>Overall winner</span>
          )}
        </div>

        <div className={styles.versusBlock}>
          <span className={styles.versusText}>vs</span>
        </div>

        <div
          className={`${styles.playerPanel} ${overallWinnerIsB ? styles.playerPanelWinner : ''}`.trim()}
        >
          <div className={styles.playerIdentity}>
            {comparison.player_b.player.photo_url ? (
              <img
                src={comparison.player_b.player.photo_url}
                alt={playerBName}
                className={styles.avatar}
              />
            ) : (
              <div className={styles.avatarFallback} aria-hidden="true">
                {getInitials(playerBName)}
              </div>
            )}

            <div className={styles.playerText}>
              <p className={styles.playerSideLabel}>Player B</p>
              <h4 className={styles.playerName}>{playerBName}</h4>

              <div className={styles.playerMeta}>
                {comparison.player_b.club?.name && (
                  <span className={styles.playerMetaItem}>
                    {comparison.player_b.club.name}
                  </span>
                )}
                {comparison.player_b.player.position && (
                  <span className={styles.playerMetaItem}>
                    {comparison.player_b.player.position}
                  </span>
                )}
                {comparison.player_b.player.age !== null &&
                  comparison.player_b.player.age !== undefined && (
                    <span className={styles.playerMetaItem}>
                      {comparison.player_b.player.age} yrs
                    </span>
                  )}
              </div>
            </div>
          </div>

          {overallWinnerIsB && (
            <span className={styles.overallWinnerBadge}>Overall winner</span>
          )}
        </div>
      </div>

      {(overallWinner?.reason || overallWinnerIsTie) && (
        <div className={styles.overallSummary}>
          <p className={styles.sectionTitle}>Overall result</p>

          <div className={styles.overallSummaryRow}>
            {overallWinnerIsTie ? (
              <span className={styles.tieBadge}>Level</span>
            ) : overallWinnerIsA ? (
              <span className={styles.winnerBadge}>{playerAName} leads</span>
            ) : overallWinnerIsB ? (
              <span className={styles.winnerBadge}>{playerBName} leads</span>
            ) : (
              <span className={styles.neutralBadge}>No overall winner</span>
            )}

            {overallWinner?.reason && (
              <p className={styles.overallReason}>{overallWinner.reason}</p>
            )}
          </div>
        </div>
      )}

      {!!metrics.length && (
        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>Key metric comparison</h4>

          <div className={styles.metricsTable}>
            {metrics.map((metric) => {
              const metricWinnerIsA = metric.winner === playerAName;
              const metricWinnerIsB = metric.winner === playerBName;
              const metricIsTie = metric.is_tie === true;

              return (
                <div key={metric.key} className={styles.metricRow}>
                  <div
                    className={`${styles.metricValueCell} ${metricWinnerIsA ? styles.metricCellWinner : ''}`.trim()}
                  >
                    <span className={styles.metricValue}>
                      {metric.player_a_formatted ?? renderValue(metric.player_a_value)}
                    </span>
                  </div>

                  <div className={styles.metricCentreCell}>
                    <span className={styles.metricLabel}>{metric.label}</span>

                    <div className={styles.metricMeta}>
                      {metricIsTie ? (
                        <span className={styles.tieBadgeSmall}>Level</span>
                      ) : metricWinnerIsA ? (
                        <span className={styles.winnerBadgeSmall}>A leads</span>
                      ) : metricWinnerIsB ? (
                        <span className={styles.winnerBadgeSmall}>B leads</span>
                      ) : (
                        <span className={styles.neutralBadgeSmall}>Unclear</span>
                      )}

                      {(metric.formatted_delta || metric.delta !== null) && (
                        <span className={styles.deltaText}>
                          Δ {metric.formatted_delta ?? renderValue(metric.delta)}
                          {metric.unit ? ` ${metric.unit}` : ''}
                        </span>
                      )}
                    </div>
                  </div>

                  <div
                    className={`${styles.metricValueCell} ${metricWinnerIsB ? styles.metricCellWinner : ''}`.trim()}
                  >
                    <span className={styles.metricValue}>
                      {metric.player_b_formatted ?? renderValue(metric.player_b_value)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {(explanation?.summary ||
        explanation?.headline ||
        explanation?.strengths?.length ||
        explanation?.watchouts?.length ||
        explanation?.notes?.length) && (
        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>
            {explanation?.headline || 'Deterministic insight'}
          </h4>

          {explanation?.summary && (
            <p className={styles.summaryText}>{explanation.summary}</p>
          )}

          {!!explanation?.strengths?.length && (
            <div className={styles.textBlock}>
              <p className={styles.textBlockTitle}>Strengths</p>
              <ul className={styles.bulletList}>
                {explanation.strengths.slice(0, 3).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {!!explanation?.watchouts?.length && (
            <div className={styles.textBlock}>
              <p className={styles.textBlockTitle}>Watch-outs</p>
              <ul className={styles.bulletList}>
                {explanation.watchouts.slice(0, 3).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {!!explanation?.notes?.length && (
            <div className={styles.textBlock}>
              <p className={styles.textBlockTitle}>Notes</p>
              <ul className={styles.bulletList}>
                {explanation.notes.slice(0, 2).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {(providerCoverage?.provider ||
        providerCoverage?.coverage_status ||
        freshnessText ||
        providerCoverage?.matches_sampled !== null ||
        providerCoverage?.minutes_sampled !== null) && (
        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>Coverage</h4>

          <div className={styles.coverageGrid}>
            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Provider</span>
              <span className={styles.coverageValue}>
                {renderValue(providerCoverage?.provider)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Status</span>
              <span className={styles.coverageValue}>
                {renderValue(providerCoverage?.coverage_status)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Freshness</span>
              <span className={styles.coverageValue}>
                {renderValue(freshnessText)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Matches sampled</span>
              <span className={styles.coverageValue}>
                {renderValue(providerCoverage?.matches_sampled)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Minutes sampled</span>
              <span className={styles.coverageValue}>
                {renderValue(providerCoverage?.minutes_sampled)}
              </span>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default PlayerComparisonCard;