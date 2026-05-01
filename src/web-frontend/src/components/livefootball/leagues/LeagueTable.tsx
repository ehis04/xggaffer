import React from 'react';
import type { LeagueTableRow, TeamReference } from '../../../types/livefootball';
import styles from './css/LeagueTable.module.css';

interface LeagueTableProps {
  rows: LeagueTableRow[];
  title?: string;
  emptyMessage?: string;
  getTeamHref?: (team: TeamReference) => string | undefined;
}

const LeagueTable: React.FC<LeagueTableProps> = ({
  rows,
  title,
  emptyMessage = 'No table rows are available.',
  getTeamHref,
}) => {
  const bottomThreshold = rows.length >= 3 ? rows.length - 2 : rows.length;

  const renderTeamCell = (team: TeamReference) => {
    const href = getTeamHref?.(team);

    return (
      <div className={styles.teamCell}>
        {team.emblem_url ? (
          <img
            src={team.emblem_url}
            alt={`${team.name} crest`}
            className={styles.crest}
            loading="lazy"
          />
        ) : (
          <span className={styles.crestPlaceholder} aria-hidden="true">
            {team.tla?.slice(0, 1) || team.name.slice(0, 1)}
          </span>
        )}

        {href ? (
          <a href={href} className={styles.teamLink}>
            {team.short_name || team.name}
          </a>
        ) : (
          <span className={styles.teamName}>{team.short_name || team.name}</span>
        )}
      </div>
    );
  };

  return (
    <section className={styles.section}>
      {title ? <h2 className={styles.title}>{title}</h2> : null}

      {rows.length === 0 ? (
        <div className={styles.emptyState}>{emptyMessage}</div>
      ) : (
        <div className={styles.scrollWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={`${styles.stickyPos} ${styles.headerCell}`}>Pos</th>
                <th className={`${styles.stickyTeam} ${styles.headerCell}`}>Team</th>
                <th className={styles.headerCell}>P</th>
                <th className={styles.headerCell}>W</th>
                <th className={styles.headerCell}>D</th>
                <th className={styles.headerCell}>L</th>
                <th className={styles.headerCell}>GF</th>
                <th className={styles.headerCell}>GA</th>
                <th className={styles.headerCell}>GD</th>
                <th className={styles.headerCell}>Pts</th>
              </tr>
            </thead>

            <tbody>
              {rows.map((row) => {
                const isTopFour = row.position <= 4;
                const isBottomThree = row.position >= bottomThreshold;

                return (
                  <tr
                    key={`${row.team.id ?? row.team.external_id ?? row.team.name}-${row.position}`}
                    className={
                      isTopFour
                        ? styles.topFourRow
                        : isBottomThree
                          ? styles.bottomThreeRow
                          : undefined
                    }
                  >
                    <td className={`${styles.stickyPos} ${styles.bodyCell}`}>{row.position}</td>
                    <td className={`${styles.stickyTeam} ${styles.bodyCell}`}>
                      {renderTeamCell(row.team)}
                    </td>
                    <td className={styles.bodyCell}>{row.played}</td>
                    <td className={styles.bodyCell}>{row.won}</td>
                    <td className={styles.bodyCell}>{row.drawn}</td>
                    <td className={styles.bodyCell}>{row.lost}</td>
                    <td className={styles.bodyCell}>{row.goals_for}</td>
                    <td className={styles.bodyCell}>{row.goals_against}</td>
                    <td className={styles.bodyCell}>{row.goal_difference}</td>
                    <td className={`${styles.bodyCell} ${styles.pointsCell}`}>{row.points}</td>
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

export default LeagueTable;