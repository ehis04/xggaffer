import React from 'react';
import type {
  PlayerDataMetric,
  PlayerSeasonSummary,
} from '../../types/playerdata';
import styles from './PlayerSeasonSummaryCard.module.css';

interface PlayerSeasonSummaryCardProps {
  summary?: PlayerSeasonSummary | null;
  isLoading?: boolean;
  error?: string | null;
  title?: string;
  emptyMessage?: string;
  maxMetrics?: number;
  className?: string;
}

const DEFAULT_EMPTY_MESSAGE = 'No player season summary is available for the selected filters.';

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
  if (parts.length === 0) return '?';

  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
};

const getDisplayName = (summary?: PlayerSeasonSummary | null): string => {
  return (
    summary?.player.display_name ||
    summary?.player.full_name ||
    summary?.player.short_name ||
    'Unknown player'
  );
};

const getVisibleMetrics = (
  metrics?: PlayerDataMetric[],
  maxMetrics: number = 6,
): PlayerDataMetric[] => {
  if (!metrics?.length) return [];

  return metrics
    .filter((metric) => metric.is_available !== false)
    .filter(
      (metric) =>
        metric.formatted_value !== null &&
        metric.formatted_value !== undefined &&
        metric.formatted_value !== '',
    )
    .slice(0, maxMetrics);
};

const renderMetaValue = (value?: string | number | null): string => {
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
};

const PlayerSeasonSummaryCard: React.FC<PlayerSeasonSummaryCardProps> = ({
  summary,
  isLoading = false,
  error = null,
  title = 'Season summary',
  emptyMessage = DEFAULT_EMPTY_MESSAGE,
  maxMetrics = 6,
  className,
}) => {
  if (isLoading) {
    return (
      <section className={`${styles.card} ${className ?? ''}`.trim()}>
        <div className={styles.loadingState}>Loading player season summary…</div>
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

  if (!summary || summary.has_summary_data === false) {
    return (
      <section className={`${styles.card} ${className ?? ''}`.trim()}>
        <div className={styles.emptyState}>
          <h3 className={styles.sectionTitle}>{title}</h3>
          <p className={styles.emptyMessage}>{emptyMessage}</p>

          {!!summary?.missing_reasons?.length && (
            <ul className={styles.reasonList}>
              {summary.missing_reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
        </div>
      </section>
    );
  }

  const displayName = getDisplayName(summary);
  const metrics = getVisibleMetrics(summary.metrics, maxMetrics);
  const explanation = summary.explanation;
  const providerCoverage = summary.provider_coverage;
  const freshnessText =
    providerCoverage?.freshness_label || formatDateTime(providerCoverage?.last_synced_at);

  return (
    <section className={`${styles.card} ${className ?? ''}`.trim()}>
      <div className={styles.header}>
        <div className={styles.identityBlock}>
          {summary.player.photo_url ? (
            <img
              src={summary.player.photo_url}
              alt={displayName}
              className={styles.avatar}
            />
          ) : (
            <div className={styles.avatarFallback} aria-hidden="true">
              {getInitials(displayName)}
            </div>
          )}

          <div className={styles.identityText}>
            <p className={styles.eyebrow}>{title}</p>
            <h3 className={styles.playerName}>{displayName}</h3>

            <div className={styles.identityMeta}>
              {summary.club?.name && (
                <span className={styles.identityMetaItem}>{summary.club.name}</span>
              )}
              {summary.player.position && (
                <span className={styles.identityMetaItem}>{summary.player.position}</span>
              )}
              {summary.player.age !== null && summary.player.age !== undefined && (
                <span className={styles.identityMetaItem}>{summary.player.age} yrs</span>
              )}
              {summary.player.nationality && (
                <span className={styles.identityMetaItem}>{summary.player.nationality}</span>
              )}
            </div>
          </div>
        </div>

        <div className={styles.contextBadges}>
          {summary.context?.season && (
            <span className={styles.badge}>{summary.context.season}</span>
          )}
          {summary.context?.competition_name && (
            <span className={styles.badge}>{summary.context.competition_name}</span>
          )}
          {summary.context?.provider && (
            <span className={styles.badgeMuted}>{summary.context.provider}</span>
          )}
        </div>
      </div>

      {!!metrics.length && (
        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>Key metrics</h4>
          <div className={styles.metricsGrid}>
            {metrics.map((metric) => (
              <div key={metric.key} className={styles.metricCard}>
                <span className={styles.metricLabel}>{metric.label}</span>
                <span className={styles.metricValue}>
                  {metric.formatted_value || renderMetaValue(metric.value)}
                </span>
              </div>
            ))}
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
        providerCoverage?.minutes_sampled !== null ||
        providerCoverage?.coverage_notes?.length) && (
        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>Coverage</h4>

          <div className={styles.coverageGrid}>
            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Provider</span>
              <span className={styles.coverageValue}>
                {renderMetaValue(providerCoverage?.provider)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Status</span>
              <span className={styles.coverageValue}>
                {renderMetaValue(providerCoverage?.coverage_status)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Freshness</span>
              <span className={styles.coverageValue}>
                {renderMetaValue(freshnessText)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Matches sampled</span>
              <span className={styles.coverageValue}>
                {renderMetaValue(providerCoverage?.matches_sampled)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Minutes sampled</span>
              <span className={styles.coverageValue}>
                {renderMetaValue(providerCoverage?.minutes_sampled)}
              </span>
            </div>
          </div>

          {!!providerCoverage?.coverage_notes?.length && (
            <ul className={styles.bulletList}>
              {providerCoverage.coverage_notes.slice(0, 2).map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
};

export default PlayerSeasonSummaryCard;