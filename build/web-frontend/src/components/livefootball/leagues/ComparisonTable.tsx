import React, { useMemo, useState } from 'react';
import LeagueTable from './LeagueTable';
import type {
  LeagueExpectedTableMetadata,
  LeagueExpectedTableRow,
  LeagueTableRow,
} from '../../../types/livefootball';
import styles from './css/ComparisonTable.module.css';

interface ComparisonTableProps {
  actualRows: LeagueTableRow[];
  expectedRows: LeagueExpectedTableRow[];
  mode: string;
  metadata: LeagueExpectedTableMetadata;
}

const formatModeLabel = (mode: string): string => {
  if (mode === 'pre_season') {
    return 'Pre-season';
  }
  if (mode === 'current_expected') {
    return 'Current expected';
  }
  if (mode === 'as_of_matchweek') {
    return 'As of matchweek';
  }
  return mode;
};

const ComparisonTable: React.FC<ComparisonTableProps> = ({
  actualRows,
  expectedRows,
  mode,
  metadata,
}) => {
  const [mobileTab, setMobileTab] = useState<'actual' | 'expected'>('actual');

  const expectedLeagueRows = useMemo<LeagueTableRow[]>(() => {
    return expectedRows.map((row) => {
      const played = Math.round(row.simulated_wins + row.simulated_draws + row.simulated_losses);
      const goalsFor = Math.round(row.simulated_goals_for);
      const goalsAgainst = Math.round(row.simulated_goals_against);

      return {
        position: row.predicted_position,
        team: row.team,
        played,
        won: Math.round(row.simulated_wins),
        drawn: Math.round(row.simulated_draws),
        lost: Math.round(row.simulated_losses),
        goals_for: goalsFor,
        goals_against: goalsAgainst,
        goal_difference: goalsFor - goalsAgainst,
        points: Math.round(row.predicted_points),
        form: '',
      };
    });
  }, [expectedRows]);

  const actualSourceNote = metadata.actual_table_source;
  const expectedSourceNote = [
    metadata.expected_table_source,
    metadata.data_cutoff_date ? `Cut-off ${metadata.data_cutoff_date}` : null,
    metadata.based_on_matchweek !== null && metadata.based_on_matchweek !== undefined
      ? `Based on matchweek ${metadata.based_on_matchweek}`
      : null,
    metadata.remaining_fixtures !== null && metadata.remaining_fixtures !== undefined
      ? `${metadata.remaining_fixtures} remaining fixtures`
      : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <section className={styles.section}>
      <div className={styles.mobileToggle}>
        <button
          type="button"
          className={`${styles.toggleButton} ${mobileTab === 'actual' ? styles.toggleButtonActive : ''}`}
          onClick={() => setMobileTab('actual')}
        >
          Actual
        </button>
        <button
          type="button"
          className={`${styles.toggleButton} ${mobileTab === 'expected' ? styles.toggleButtonActive : ''}`}
          onClick={() => setMobileTab('expected')}
        >
          Expected
        </button>
      </div>

      <div className={styles.grid}>
        <div
          className={`${styles.panel} ${mobileTab === 'actual' ? styles.mobileVisible : styles.mobileHidden}`}
        >
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>Actual</h2>
            <p className={styles.panelMeta}>{actualSourceNote}</p>
          </div>

          <LeagueTable
            rows={actualRows}
            emptyMessage="No actual table rows are available."
          />
        </div>

        <div
          className={`${styles.panel} ${mobileTab === 'expected' ? styles.mobileVisible : styles.mobileHidden}`}
        >
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>Expected ({formatModeLabel(mode)})</h2>
            <p className={styles.panelMeta}>{expectedSourceNote}</p>
          </div>

          <LeagueTable
            rows={expectedLeagueRows}
            emptyMessage="No expected table rows are available."
          />
        </div>
      </div>
    </section>
  );
};

export default ComparisonTable;