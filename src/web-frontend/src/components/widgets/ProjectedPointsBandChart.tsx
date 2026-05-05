import type { TeamProjection } from '../../services/api/widgetApi';
import styles from './css/ProjectedPointsBandChart.module.css';

const CHART_BAR_HEIGHT_PX = 28;
const CHART_BAR_GAP_PX = 6;
const CHART_MIN_POINTS_PADDING = 5;
const MOBILE_TEAM_NAME_MAX_CHARS = 14;

function truncate(name: string, max: number): string {
  return name.length > max ? `${name.slice(0, max)}…` : name;
}

interface ProjectedPointsBandChartProps {
  teams: TeamProjection[];
}

export default function ProjectedPointsBandChart({ teams }: ProjectedPointsBandChartProps) {
  const allP10 = teams.map(t => t.projected_points_p10 ?? t.projected_points_median);
  const allP90 = teams.map(t => t.projected_points_p90 ?? t.projected_points_median);
  const minPoints = Math.max(0, Math.min(...allP10) - CHART_MIN_POINTS_PADDING);
  const maxPoints = Math.max(...allP90) + CHART_MIN_POINTS_PADDING;
  const range = maxPoints - minPoints || 1;

  function toPercent(value: number): number {
    return ((value - minPoints) / range) * 100;
  }

  return (
    <div className={styles.chart}>
      {teams.map(team => {
        const p10 = team.projected_points_p10 ?? team.projected_points_median;
        const p90 = team.projected_points_p90 ?? team.projected_points_median;
        const median = team.projected_points_median;

        const leftPct = toPercent(p10);
        const widthPct = toPercent(p90) - leftPct;
        const medianPct = toPercent(median);

        return (
          <div
            key={team.team_name}
            className={styles.row}
            style={{ height: CHART_BAR_HEIGHT_PX, marginBottom: CHART_BAR_GAP_PX }}
          >
            <span className={styles.teamNameFull}>{team.team_name}</span>
            <span className={styles.teamNameShort}>
              {truncate(team.team_name, MOBILE_TEAM_NAME_MAX_CHARS)}
            </span>
            <div className={styles.track}>
              <div
                className={styles.band}
                style={{ left: `${leftPct}%`, width: `${Math.max(widthPct, 0.5)}%` }}
              />
              <div
                className={styles.median}
                style={{ left: `${medianPct}%` }}
                title={`Median: ${median.toFixed(1)} pts`}
              />
            </div>
            <span className={styles.ptLabel}>{median.toFixed(0)}</span>
          </div>
        );
      })}
      <div className={styles.axisRow}>
        <span className={styles.axisLabel}>{minPoints.toFixed(0)}</span>
        <div className={styles.axisTrack} />
        <span className={styles.axisLabel}>{maxPoints.toFixed(0)}</span>
      </div>
    </div>
  );
}