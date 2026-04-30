/**
 * LeagueTable.tsx
 *
 * Renders a standings table for a given competition season.
 * Supports optional form column and row-count capping via maxRows.
 *
 * CSS: LeagueTable.module.css  (prefix: lflt-)
 */

import React from 'react';
import type {
  CompetitionTableResponse,
  LeagueTableRow,
} from '../../types/livefootball';
import styles from './css/LeagueTable.module.css';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatForm = (value?: string | null): string => value?.trim() || '—';

const getTeamLabel = (row: LeagueTableRow): string =>
  row.team.short_name?.trim() || row.team.tla?.trim() || row.team.name;

/** Colour each form character independently — W green, D grey, L red */
const FormChips: React.FC<{ form: string }> = ({ form }) => (
  <>
    {form.split('').map((char, idx) => {
      const mod =
        char === 'W' ? styles['lflt-form-w']
        : char === 'L' ? styles['lflt-form-l']
        : styles['lflt-form-d'];
      return (
        // index-as-key is fine here: form string is a fixed-length display value
        // eslint-disable-next-line react/no-array-index-key
        <span key={idx} className={`${styles['lflt-form-chip']} ${mod}`}>
          {char}
        </span>
      );
    })}
  </>
);

// ─── Props ────────────────────────────────────────────────────────────────────

export interface LeagueTableProps {
  table: CompetitionTableResponse | null;
  isLoading?: boolean;
  error?: string | null;
  title?: string;
  emptyMessage?: string;
  className?: string;
  maxRows?: number;
  showForm?: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

const LeagueTable: React.FC<LeagueTableProps> = ({
  table,
  isLoading = false,
  error = null,
  title = 'League Table',
  emptyMessage = 'No table data is available for this competition yet.',
  className,
  maxRows,
  showForm = true,
}) => {
  // ── State variants ──
  if (isLoading) {
    return (
      <section className={`${styles['lflt-root']} ${className ?? ''}`}>
        <h2 className={styles['lflt-title']}>{title}</h2>
        <div className={styles['lflt-state']}>Loading table…</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className={`${styles['lflt-root']} ${className ?? ''}`}>
        <h2 className={styles['lflt-title']}>{title}</h2>
        <div className={styles['lflt-state-error']} role="alert">{error}</div>
      </section>
    );
  }

  if (!table || table.rows.length === 0) {
    return (
      <section className={`${styles['lflt-root']} ${className ?? ''}`}>
        <h2 className={styles['lflt-title']}>{title}</h2>
        <div className={styles['lflt-state']}>{emptyMessage}</div>
      </section>
    );
  }

  const rows =
    typeof maxRows === 'number' && maxRows > 0
      ? table.rows.slice(0, maxRows)
      : table.rows;

  return (
    <section className={`${styles['lflt-root']} ${className ?? ''}`}>
      {/* Panel header */}
      <div className={styles['lflt-panel-header']}>
        <h2 className={styles['lflt-title']}>{title}</h2>
        <p className={styles['lflt-competition-meta']}>
          {table.competition.name}
          {table.competition.area_name ? ` · ${table.competition.area_name}` : ''}
          {table.season_label ? ` · ${table.season_label}` : ''}
          {table.snapshot_label ? ` · ${table.snapshot_label}` : ''}
        </p>
      </div>

      {/* Table */}
      <div className={styles['lflt-table-wrapper']}>
        <table className={styles['lflt-table']}>
          <thead>
            <tr className={styles['lflt-thead-row']}>
              <th className={`${styles['lflt-th']} ${styles['lflt-th--pos']}`} scope="col">#</th>
              <th className={`${styles['lflt-th']} ${styles['lflt-th--team']}`} scope="col">Team</th>
              <th className={styles['lflt-th']} scope="col">P</th>
              <th className={styles['lflt-th']} scope="col">W</th>
              <th className={styles['lflt-th']} scope="col">D</th>
              <th className={styles['lflt-th']} scope="col">L</th>
              <th className={styles['lflt-th']} scope="col">GD</th>
              <th className={`${styles['lflt-th']} ${styles['lflt-th--pts']}`} scope="col">Pts</th>
              {showForm && <th className={styles['lflt-th']} scope="col">Form</th>}
            </tr>
          </thead>

          <tbody>
            {rows.map((row, idx) => {
              const teamKey = `${row.position}-${row.team.id ?? row.team.external_id ?? row.team.name}`;
              const isTop = idx < 4;       // rough CL zone hint
              const isBottom = idx >= rows.length - 3;
              return (
                <tr
                  key={teamKey}
                  className={`${styles['lflt-row']} ${isTop ? styles['lflt-row--top'] : ''} ${isBottom ? styles['lflt-row--bottom'] : ''}`}
                >
                  <td className={`${styles['lflt-td']} ${styles['lflt-td--pos']}`}>
                    {row.position}
                  </td>
                  <td className={`${styles['lflt-td']} ${styles['lflt-td--team']}`}>
                    <span className={styles['lflt-team-name']}>{getTeamLabel(row)}</span>
                    {row.team.name !== getTeamLabel(row) && (
                      <span className={styles['lflt-team-full']}>{row.team.name}</span>
                    )}
                  </td>
                  <td className={styles['lflt-td']}>{row.played}</td>
                  <td className={styles['lflt-td']}>{row.won}</td>
                  <td className={styles['lflt-td']}>{row.drawn}</td>
                  <td className={styles['lflt-td']}>{row.lost}</td>
                  <td className={`${styles['lflt-td']} ${row.goal_difference > 0 ? styles['lflt-td--pos-gd'] : row.goal_difference < 0 ? styles['lflt-td--neg-gd'] : ''}`}>
                    {row.goal_difference > 0 ? `+${row.goal_difference}` : row.goal_difference}
                  </td>
                  <td className={`${styles['lflt-td']} ${styles['lflt-td--pts']}`}>
                    {row.points}
                  </td>
                  {showForm && (
                    <td className={styles['lflt-td']}>
                      <div className={styles['lflt-form-row']}>
                        {formatForm(row.form) === '—'
                          ? <span className={styles['lflt-form-empty']}>—</span>
                          : <FormChips form={formatForm(row.form)} />
                        }
                      </div>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default LeagueTable;