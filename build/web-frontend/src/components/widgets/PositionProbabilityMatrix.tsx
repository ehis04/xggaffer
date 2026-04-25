import type { TeamProjection } from '../../services/api/widgetApi';
import styles from './css/PositionProbabilityMatrix.module.css';

const MATRIX_CELL_MIN_WIDTH_PX = 36;
const MATRIX_HIGHLIGHT_THRESHOLD = 0.15;
const MOBILE_TEAM_NAME_MAX_CHARS = 14;

function truncate(name: string, max: number): string {
  return name.length > max ? `${name.slice(0, max)}…` : name;
}

interface PositionProbabilityMatrixProps {
  teams: TeamProjection[];
}

export default function PositionProbabilityMatrix({ teams }: PositionProbabilityMatrixProps) {
  const n = teams.length;
  const positions = Array.from({ length: n }, (_, i) => i + 1);

  return (
    <div className={styles.scrollWrapper}>
      <table className={styles.matrix}>
        <thead>
          <tr>
            <th className={styles.cornerCell} />
            {positions.map(pos => (
              <th key={pos} className={styles.colHeader} style={{ minWidth: MATRIX_CELL_MIN_WIDTH_PX }}>
                {pos}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {teams.map(team => {
            const dist = team.position_distribution;
            const isEmpty = Object.keys(dist).length === 0;

            const probs = positions.map(pos => {
              const val = dist[String(pos)];
              return val !== undefined ? val : 0;
            });

            const peakIdx = isEmpty
              ? -1
              : probs.reduce((best, val, idx) => (val > probs[best] ? idx : best), 0);

            return (
              <tr key={team.team_name}>
                <th className={styles.rowHeader}>
                  <span className={styles.teamNameFull}>{team.team_name}</span>
                  <span className={styles.teamNameShort}>
                    {truncate(team.team_name, MOBILE_TEAM_NAME_MAX_CHARS)}
                  </span>
                </th>
                {positions.map((pos, idx) => {
                  const prob = probs[idx];
                  const isPeak = idx === peakIdx;
                  const isHigh = prob >= MATRIX_HIGHLIGHT_THRESHOLD;

                  const cellClass = [
                    styles.cell,
                    isPeak ? styles.cellPeak : '',
                    !isPeak && isHigh ? styles.cellHigh : '',
                  ].filter(Boolean).join(' ');

                  return (
                    <td
                      key={pos}
                      className={cellClass}
                      style={{ minWidth: MATRIX_CELL_MIN_WIDTH_PX }}
                    >
                      {isEmpty ? '—' : `${(prob * 100).toFixed(0)}%`}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}