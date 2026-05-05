import React from 'react';
import type { ProviderCoverage } from '../../types/playerdata';
import styles from './ProviderCoverageBlock.module.css';

interface ProviderCoverageBlockProps {
  coverage?: ProviderCoverage | null;
  title?: string;
  emptyMessage?: string;
  compact?: boolean;
  hideWhenEmpty?: boolean;
  maxNotes?: number;
  className?: string;
}

const DEFAULT_EMPTY_MESSAGE = 'No provider coverage details are available.';

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

const hasCoverageContent = (coverage?: ProviderCoverage | null): boolean => {
  return Boolean(
    coverage?.provider ||
      coverage?.coverage_status ||
      coverage?.freshness_label ||
      coverage?.source_updated_at ||
      coverage?.last_synced_at ||
      coverage?.matches_sampled !== null ||
      coverage?.minutes_sampled !== null ||
      coverage?.coverage_notes?.length,
  );
};

const ProviderCoverageBlock: React.FC<ProviderCoverageBlockProps> = ({
  coverage,
  title = 'Coverage',
  emptyMessage = DEFAULT_EMPTY_MESSAGE,
  compact = false,
  hideWhenEmpty = true,
  maxNotes = 2,
  className,
}) => {
  const hasCoverage = hasCoverageContent(coverage);

  if (!hasCoverage) {
    if (hideWhenEmpty) return null;

    return (
      <section className={`${styles.block} ${compact ? styles.compact : ''} ${className ?? ''}`.trim()}>
        <h4 className={styles.title}>{title}</h4>
        <p className={styles.emptyMessage}>{emptyMessage}</p>
      </section>
    );
  }

  const freshnessText =
    coverage?.freshness_label ||
    formatDateTime(coverage?.last_synced_at) ||
    formatDateTime(coverage?.source_updated_at);

  return (
    <section className={`${styles.block} ${compact ? styles.compact : ''} ${className ?? ''}`.trim()}>
      <h4 className={styles.title}>{title}</h4>

      <div className={styles.grid}>
        <div className={styles.item}>
          <span className={styles.label}>Provider</span>
          <span className={styles.value}>{formatValue(coverage?.provider)}</span>
        </div>

        <div className={styles.item}>
          <span className={styles.label}>Status</span>
          <span className={styles.value}>{formatValue(coverage?.coverage_status)}</span>
        </div>

        <div className={styles.item}>
          <span className={styles.label}>Freshness</span>
          <span className={styles.value}>{formatValue(freshnessText)}</span>
        </div>

        <div className={styles.item}>
          <span className={styles.label}>Matches sampled</span>
          <span className={styles.value}>{formatValue(coverage?.matches_sampled)}</span>
        </div>

        <div className={styles.item}>
          <span className={styles.label}>Minutes sampled</span>
          <span className={styles.value}>{formatValue(coverage?.minutes_sampled)}</span>
        </div>
      </div>

      {!!coverage?.coverage_notes?.length && (
        <ul className={styles.notes}>
          {coverage.coverage_notes.slice(0, maxNotes).map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </section>
  );
};

export default ProviderCoverageBlock;