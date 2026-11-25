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
  const isPreSeasonToDate = mode === 'pre_season' && metadata.projection_window === 'to_date';

  const actualPlayedLookup = useMemo(() => {
    const byTeamId = new Map<number, number>();
    const byTeamName = new Map<string, number>();

    actualRows.forEach((row) => {
      const played = Number(row.played);
      if (!Number.isFinite(played)) {
        return;
      }

      if (typeof row.team.id === 'number') {
        byTeamId.set(row.team.id, played);
      }

      const loweredName = (row.team.name || '').trim().toLowerCase();
      if (loweredName) {
        byTeamName.set(loweredName, played);
      }
    });

    return { byTeamId, byTeamName };
  }, [actualRows]);

  const expectedLeagueRows = useMemo<LeagueTableRow[]>(() => {
    const resolveActualPlayedForExpected = (row: LeagueExpectedTableRow): number | null => {
      if (typeof row.team.id === 'number') {
        const byId = actualPlayedLookup.byTeamId.get(row.team.id);
        if (byId !== undefined) return byId;
      }

      const loweredName = (row.team.name || '').trim().toLowerCase();
      if (!loweredName) return null;
      return actualPlayedLookup.byTeamName.get(loweredName) ?? null;
    };

    return expectedRows.map((row) => {
      const simulatedPlayed = Math.round(row.simulated_wins + row.simulated_draws + row.simulated_losses);
      const actualPlayed = isPreSeasonToDate ? resolveActualPlayedForExpected(row) : null;
      const played = actualPlayed ?? simulatedPlayed;
      const goalsFor = Math.round(row.simulated_goals_for);
      const goalsAgainst = Math.round(row.simulated_goals_against);
      let won = Math.round(row.simulated_wins);
      const drawn = Math.round(row.simulated_draws);
      let lost = Math.round(row.simulated_losses);

      if (actualPlayed !== null) {
        const diff = played - (won + drawn + lost);
        if (diff > 0) {
          lost += diff;
        } else if (diff < 0) {
          let remaining = -diff;
          const reduceLost = Math.min(lost, remaining);
          lost -= reduceLost;
          remaining -= reduceLost;
          if (remaining > 0) {
            const reduceWon = Math.min(won, remaining);
            won -= reduceWon;
          }
        }
      }

      return {
        position: row.predicted_position,
        team: row.team,
        played,
        won,
        drawn,
        lost,
        goals_for: goalsFor,
        goals_against: goalsAgainst,
        goal_difference: goalsFor - goalsAgainst,
        points: Math.round(row.predicted_points),
        form: '',
      };
    });
  }, [expectedRows, isPreSeasonToDate, actualPlayedLookup]);

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
