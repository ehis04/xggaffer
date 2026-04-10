import React from 'react';
import type {
  CompetitionTableResponse,
  LeagueTableRow,
} from '../../types/livefootball';

const formatForm = (value?: string | null): string => {
  const trimmed = value?.trim();
  return trimmed ? trimmed : '—';
};

const getTeamLabel = (row: LeagueTableRow): string => {
  if (row.team.short_name?.trim()) {
    return row.team.short_name;
  }

  if (row.team.tla?.trim()) {
    return row.team.tla;
  }

  return row.team.name;
};

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
  if (isLoading) {
    return (
      <section className={className}>
        <h2>{title}</h2>
        <div>Loading table…</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className={className}>
        <h2>{title}</h2>
        <div role="alert">{error}</div>
      </section>
    );
  }

  if (!table || table.rows.length === 0) {
    return (
      <section className={className}>
        <h2>{title}</h2>
        <div>{emptyMessage}</div>
      </section>
    );
  }

  const rows = typeof maxRows === 'number' && maxRows > 0
    ? table.rows.slice(0, maxRows)
    : table.rows;

  return (
    <section className={className}>
      <div>
        <h2>{title}</h2>
        <p>
          {table.competition.name}
          {table.competition.area_name ? ` · ${table.competition.area_name}` : ''}
          {table.season_label ? ` · ${table.season_label}` : ''}
          {table.snapshot_label ? ` · ${table.snapshot_label}` : ''}
        </p>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th scope="col">Pos</th>
              <th scope="col">Team</th>
              <th scope="col">P</th>
              <th scope="col">W</th>
              <th scope="col">D</th>
              <th scope="col">L</th>
              <th scope="col">GD</th>
              <th scope="col">Pts</th>
              {showForm ? <th scope="col">Form</th> : null}
            </tr>
          </thead>

          <tbody>
            {rows.map((row) => (
              <tr key={`${row.position}-${row.team.id ?? row.team.external_id ?? row.team.name}`}>
                <td>{row.position}</td>
                <td>
                  <div>
                    <strong>{getTeamLabel(row)}</strong>
                  </div>
                  {row.team.name !== getTeamLabel(row) ? (
                    <div>
                      <small>{row.team.name}</small>
                    </div>
                  ) : null}
                </td>
                <td>{row.played}</td>
                <td>{row.won}</td>
                <td>{row.drawn}</td>
                <td>{row.lost}</td>
                <td>{row.goal_difference}</td>
                <td>
                  <strong>{row.points}</strong>
                </td>
                {showForm ? <td>{formatForm(row.form)}</td> : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default LeagueTable;