import React, { useMemo, useState } from 'react';
import type {
  LeagueComparisonDelta,
  LeagueComparisonMetrics,
} from '../../../types/livefootball';
import styles from './css/ComparisonMetrics.module.css';

type SortKey =
  | 'team'
  | 'actual_position'
  | 'expected_position'
  | 'position_delta'
  | 'absolute_position_delta'
  | 'actual_points'
  | 'expected_points'
  | 'points_delta'
  | 'absolute_points_delta';

type SortDirection = 'asc' | 'desc';

interface ComparisonMetricsProps {
  deltas: LeagueComparisonDelta[];
  comparisonMetrics: LeagueComparisonMetrics;
  emptyMessage?: string;
}

const formatMetricValue = (value: number | null): string => {
  if (value === null || Number.isNaN(value)) {
    return '—';
  }
  return String(value);
};

const ComparisonMetrics: React.FC<ComparisonMetricsProps> = ({
  deltas,
  comparisonMetrics,
  emptyMessage = 'No comparison deltas are available.',
}) => {
  const [sortKey, setSortKey] = useState<SortKey>('absolute_position_delta');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const sortedRows = useMemo(() => {
    const rows = [...deltas];

    rows.sort((a, b) => {
      const getValue = (row: LeagueComparisonDelta): string | number => {
        switch (sortKey) {
          case 'team':
            return row.team.short_name || row.team.name;
          case 'actual_position':
            return row.actual_position;
          case 'expected_position':
            return row.expected_position;
          case 'position_delta':
            return row.position_delta;
          case 'absolute_position_delta':
            return Math.abs(row.position_delta);
          case 'actual_points':
            return row.actual_points;
          case 'expected_points':
            return row.expected_points;
          case 'points_delta':
            return row.points_delta;
          case 'absolute_points_delta':
            return Math.abs(row.points_delta);
          default:
            return row.team.name;
        }
      };

      const left = getValue(a);
      const right = getValue(b);

      if (typeof left === 'string' && typeof right === 'string') {
        const result = left.localeCompare(right);
        return sortDirection === 'asc' ? result : -result;
      }

      const result = Number(left) - Number(right);
      return sortDirection === 'asc' ? result : -result;
    });

    return rows;
  }, [deltas, sortDirection, sortKey]);

  const handleSort = (nextKey: SortKey): void => {
    if (sortKey === nextKey) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }

    setSortKey(nextKey);
    setSortDirection(
      nextKey === 'team' || nextKey === 'actual_position' || nextKey === 'expected_position'
        ? 'asc'
        : 'desc'
    );
  };

  const renderSortButton = (label: string, key: SortKey) => (
    <button
      type="button"
      className={`${styles.sortButton} ${sortKey === key ? styles.sortButtonActive : ''}`}
      onClick={() => handleSort(key)}
    >
      {label}
    </button>
  );

  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <h2 className={styles.title}>Comparison metrics</h2>
      </div>

      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>Matched teams</span>
          <span className={styles.summaryValue}>{comparisonMetrics.matched_team_count}</span>
        </div>

        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>Average absolute position delta</span>
          <span className={styles.summaryValue}>
            {formatMetricValue(comparisonMetrics.average_absolute_position_delta)}
          </span>
        </div>

        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>Average absolute points delta</span>
          <span className={styles.summaryValue}>
            {formatMetricValue(comparisonMetrics.average_absolute_points_delta)}
          </span>
        </div>

        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>Points correlation</span>
          <span className={styles.summaryValue}>
            {formatMetricValue(comparisonMetrics.points_correlation)}
          </span>
        </div>
      </div>

      {sortedRows.length === 0 ? (
        <div className={styles.emptyState}>{emptyMessage}</div>
      ) : (
        <div className={styles.scrollWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>{renderSortButton('Team', 'team')}</th>
                <th>{renderSortButton('Actual pos', 'actual_position')}</th>
                <th>{renderSortButton('Expected pos', 'expected_position')}</th>
                <th>{renderSortButton('Δ pos', 'position_delta')}</th>
                <th>{renderSortButton('|Δ pos|', 'absolute_position_delta')}</th>
                <th>{renderSortButton('Actual pts', 'actual_points')}</th>
                <th>{renderSortButton('Expected pts', 'expected_points')}</th>
                <th>{renderSortButton('Δ pts', 'points_delta')}</th>
                <th>{renderSortButton('|Δ pts|', 'absolute_points_delta')}</th>
              </tr>
            </thead>

            <tbody>
              {sortedRows.map((row) => {
                const absolutePositionDelta = Math.abs(row.position_delta);
                const absolutePointsDelta = Math.abs(row.points_delta);
                const isLargeDelta = absolutePositionDelta >= 3;

                return (
                  <tr
                    key={`${row.canonical_team_name}-${row.actual_position}-${row.expected_position}`}
                    className={isLargeDelta ? styles.largeDeltaRow : undefined}
                  >
                    <td className={styles.teamCell}>{row.team.short_name || row.team.name}</td>
                    <td>{row.actual_position}</td>
                    <td>{row.expected_position}</td>
                    <td>{row.position_delta > 0 ? `+${row.position_delta}` : row.position_delta}</td>
                    <td>{absolutePositionDelta}</td>
                    <td>{row.actual_points.toFixed(1)}</td>
                    <td>{row.expected_points.toFixed(1)}</td>
                    <td>{row.points_delta > 0 ? `+${row.points_delta.toFixed(1)}` : row.points_delta.toFixed(1)}</td>
                    <td>{absolutePointsDelta.toFixed(1)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};

export default ComparisonMetrics;