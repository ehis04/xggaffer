import { FreshnessBadge } from '../../common/components/FreshnessBadge';
import DegradedBanner from './DegradedBanner';
import type { TeamProjection, WidgetFreshness } from '../../services/api/widgetApi';
import styles from './css/SimulatedLeagueTable.module.css';

const TOP_FOUR_POSITIONS = 4;
const MOBILE_TEAM_NAME_MAX_CHARS = 14;

const RELEGATION_START: Record<string, number> = {
  PL: 18,
  PD: 18,
  BL1: 16,
  SA: 18,
  FL1: 18,
};

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function truncate(name: string, max: number): string {
  return name.length > max ? `${name.slice(0, max)}…` : name;
}

interface SimulatedLeagueTableProps {
  teams: TeamProjection[];
  leagueCode: string;
  freshness: WidgetFreshness;
  adjustedTeamNames?: Set<string>;
}

export default function SimulatedLeagueTable({
  teams,
  leagueCode,
  freshness,
  adjustedTeamNames,
}: SimulatedLeagueTableProps) {
  const relegationStart = RELEGATION_START[leagueCode] ?? 18;

  return (
    <div>
      {freshness.cascade_degraded && freshness.cascade_reason && (
        <DegradedBanner reason={freshness.cascade_reason} cascade />
      )}
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>Pos</th>
              <th className={styles.th}>
                Team
                <FreshnessBadge freshness={freshness} />
              </th>
              <th className={styles.th}>Pts</th>
              <th className={`${styles.th} ${styles.rangeCol}`}>Range</th>
              <th className={styles.th}>Title%</th>
              <th className={styles.th}>Top 4%</th>
              <th className={styles.th}>Rel%</th>
            </tr>
          </thead>
          <tbody>
            {teams.map((team) => {
              const pos = team.expected_position;
              const isTop4 = pos <= TOP_FOUR_POSITIONS;
              const isRelegation = pos >= relegationStart;
              const isAdjusted = adjustedTeamNames?.has(team.team_name) ?? false;

              const rowClass = [
                styles.row,
                isTop4 ? styles.rowTop4 : '',
                isRelegation ? styles.rowRelegation : '',
              ].filter(Boolean).join(' ');

              const hasRange =
                team.projected_points_p10 !== null &&
                team.projected_points_p90 !== null;

              return (
                <tr key={team.team_name} className={rowClass}>
                  <td className={styles.td}>{pos}</td>
                  <td className={styles.td}>
                    <span className={styles.teamName}>
                      {team.team_name}
                      {isAdjusted && <span className={styles.asterisk}>*</span>}
                    </span>
                    <span className={styles.teamNameMobile}>
                      {truncate(team.team_name, MOBILE_TEAM_NAME_MAX_CHARS)}
                      {isAdjusted && <span className={styles.asterisk}>*</span>}
                    </span>
                  </td>
                  <td className={styles.td}>
                    {team.projected_points_median.toFixed(1)}
                  </td>
                  <td className={`${styles.td} ${styles.rangeCol}`}>
                    {hasRange
                      ? `${team.projected_points_p10} – ${team.projected_points_p90}`
                      : '—'}
                  </td>
                  <td className={styles.td}>{pct(team.title_prob)}</td>
                  <td className={styles.td}>{pct(team.top4_prob)}</td>
                  <td className={styles.td}>{pct(team.relegation_prob)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}