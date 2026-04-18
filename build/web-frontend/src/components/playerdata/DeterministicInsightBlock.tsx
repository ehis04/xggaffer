import React from 'react';
import type {
  PlayerDataExplanation,
  ProviderCoverage,
} from '../../types/playerdata';
import styles from './DeterministicInsightBlock.module.css';

interface DeterministicInsightBlockProps {
  explanation?: PlayerDataExplanation | null;
  providerCoverage?: ProviderCoverage | null;
  title?: string;
  emptyMessage?: string;
  showCoverage?: boolean;
  compact?: boolean;
  className?: string;
}

const DEFAULT_EMPTY_MESSAGE =
  'No deterministic explanation is available for this selection.';

const formatValue = (value?: string | number | null): string => {
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
};

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

const hasExplanationContent = (
  explanation?: PlayerDataExplanation | null,
): boolean => {
  return Boolean(
    explanation?.headline ||
      explanation?.summary ||
      explanation?.strengths?.length ||
      explanation?.watchouts?.length ||
      explanation?.notes?.length,
  );
};

const hasCoverageContent = (
  providerCoverage?: ProviderCoverage | null,
): boolean => {
  return Boolean(
    providerCoverage?.provider ||
      providerCoverage?.coverage_status ||
      providerCoverage?.freshness_label ||
      providerCoverage?.last_synced_at ||
      providerCoverage?.source_updated_at ||
      providerCoverage?.matches_sampled !== null ||
      providerCoverage?.minutes_sampled !== null ||
      providerCoverage?.coverage_notes?.length,
  );
};

const DeterministicInsightBlock: React.FC<DeterministicInsightBlockProps> = ({
  explanation,
  providerCoverage,
  title = 'Deterministic insight',
  emptyMessage = DEFAULT_EMPTY_MESSAGE,
  showCoverage = true,
  compact = false,
  className,
}) => {
  const hasExplanation = hasExplanationContent(explanation);
  const hasCoverage = hasCoverageContent(providerCoverage);

  if (!hasExplanation && (!showCoverage || !hasCoverage)) {
    return (
      <section className={`${styles.block} ${className ?? ''}`.trim()}>
        <h4 className={styles.title}>{title}</h4>
        <p className={styles.emptyMessage}>{emptyMessage}</p>
      </section>
    );
  }

  const freshnessText =
    providerCoverage?.freshness_label ||
    formatDateTime(providerCoverage?.last_synced_at) ||
    formatDateTime(providerCoverage?.source_updated_at);

  const rootClassName = [
    styles.block,
    compact ? styles.compact : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <section className={rootClassName}>
      <h4 className={styles.title}>
        {explanation?.headline || title}
      </h4>

      {explanation?.summary && (
        <p className={styles.summary}>{explanation.summary}</p>
      )}

      {!!explanation?.strengths?.length && (
        <div className={styles.section}>
          <p className={styles.sectionLabel}>Strengths</p>
          <ul className={styles.list}>
            {explanation.strengths
              .slice(0, compact ? 2 : 3)
              .map((item) => (
                <li key={item}>{item}</li>
              ))}
          </ul>
        </div>
      )}

      {!!explanation?.watchouts?.length && (
        <div className={styles.section}>
          <p className={styles.sectionLabel}>Watch-outs</p>
          <ul className={styles.list}>
            {explanation.watchouts
              .slice(0, compact ? 2 : 3)
              .map((item) => (
                <li key={item}>{item}</li>
              ))}
          </ul>
        </div>
      )}

      {!!explanation?.notes?.length && (
        <div className={styles.section}>
          <p className={styles.sectionLabel}>Notes</p>
          <ul className={styles.list}>
            {explanation.notes
              .slice(0, compact ? 1 : 2)
              .map((item) => (
                <li key={item}>{item}</li>
              ))}
          </ul>
        </div>
      )}

      {showCoverage && hasCoverage && (
        <div className={styles.coverageSection}>
          <p className={styles.sectionLabel}>Coverage</p>

          <div className={styles.coverageGrid}>
            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Provider</span>
              <span className={styles.coverageValue}>
                {formatValue(providerCoverage?.provider)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Status</span>
              <span className={styles.coverageValue}>
                {formatValue(providerCoverage?.coverage_status)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Freshness</span>
              <span className={styles.coverageValue}>
                {formatValue(freshnessText)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Matches</span>
              <span className={styles.coverageValue}>
                {formatValue(providerCoverage?.matches_sampled)}
              </span>
            </div>

            <div className={styles.coverageItem}>
              <span className={styles.coverageLabel}>Minutes</span>
              <span className={styles.coverageValue}>
                {formatValue(providerCoverage?.minutes_sampled)}
              </span>
            </div>
          </div>

          {!!providerCoverage?.coverage_notes?.length && (
            <ul className={styles.list}>
              {providerCoverage.coverage_notes
                .slice(0, compact ? 1 : 2)
                .map((note) => (
                  <li key={note}>{note}</li>
                ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
};

export default DeterministicInsightBlock;