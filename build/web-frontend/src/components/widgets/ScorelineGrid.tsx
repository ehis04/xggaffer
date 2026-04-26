import styles from './css/ScorelineGrid.module.css';

const SCORELINE_GRID_DEFAULT_MAX_GOALS = 5;

interface ScorelineGridProps {
  matrix: number[][];
  homeTeam: string;
  awayTeam: string;
  maxGoals?: number;
}

interface TopScoresCardProps {
  topScorelines: Array<{ scoreline: string; prob: number }>;
}

function findHighestCell(matrix: number[][]): [number, number] {
  let maxVal = -1;
  let maxRow = 0;
  let maxCol = 0;
  matrix.forEach((row, r) => {
    row.forEach((val, c) => {
      if (val > maxVal) { maxVal = val; maxRow = r; maxCol = c; }
    });
  });
  return [maxRow, maxCol];
}

export function TopScoresCard({ topScorelines }: TopScoresCardProps) {
  return (
    <div className={styles.topScoresCard}>
      <p className={styles.topScoresLabel}>Top scorelines</p>
      {topScorelines.map(({ scoreline, prob }) => (
        <div key={scoreline} className={styles.topScoreRow}>
          <span className={styles.scorelineLabel}>{scoreline}</span>
          <span className={styles.scorelineProb}>{(prob * 100).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

export function ScorelineGrid({ matrix, homeTeam, awayTeam, maxGoals = SCORELINE_GRID_DEFAULT_MAX_GOALS }: ScorelineGridProps) {
  const size = maxGoals + 1;
  const trimmed = matrix.slice(0, size).map(row => row.slice(0, size));
  const [highRow, highCol] = findHighestCell(trimmed);
  const awayGoals = Array.from({ length: size }, (_, i) => i);

  const topScorelines = trimmed
    .flatMap((row, r) => row.map((prob, c) => ({ scoreline: `${r}-${c}`, prob })))
    .sort((a, b) => b.prob - a.prob)
    .slice(0, 3);

  return (
    <>
      <div className={styles.gridWrapper}>
        <table className={styles.grid}>
          <thead>
            <tr>
              <th className={styles.cornerCell}>{homeTeam} ↓ / {awayTeam} →</th>
              {awayGoals.map(ag => (
                <th key={ag} className={styles.headerCell}>{ag}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {trimmed.map((row, hg) => (
              <tr key={hg}>
                <th className={styles.headerCell}>{hg}</th>
                {row.map((prob, ag) => (
                  <td
                    key={ag}
                    className={`${styles.cell} ${hg === highRow && ag === highCol ? styles.cellHighlight : ''}`}
                  >
                    {(prob * 100).toFixed(1)}%
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className={styles.mobileOnly}>
        <TopScoresCard topScorelines={topScorelines} />
      </div>
    </>
  );
}