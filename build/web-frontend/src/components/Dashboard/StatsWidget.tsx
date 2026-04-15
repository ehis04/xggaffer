import { StatCard } from "./StatCard";
import type { StatsWidgetProps } from "./types/DashboardTypes";
import './css/StatsWidget.css';

export const StatsWidget = ({ squad, season }: StatsWidgetProps) => {
  const played = season.wins + season.draws + season.losses;
  const winRate = played > 0 ? Math.round((season.wins / played) * 100) : 0;

  const fitnessHealth = squad.avg_fitness >= 80;
  const availabilityRatio = `${squad.available}/${squad.total}`;

  return (
    <div className="stats-widget">
      <div className="stats-widget-row">
        <span className="stats-widget-row-lbl">Squad health</span>
        <div className="stats-widget-cards">
          <StatCard
            label="Avg fitness"
            value={`${squad.avg_fitness}`}
            delta={fitnessHealth ? "Good shape" : "Below target"}
            deltaPositive={fitnessHealth}
          />
          <StatCard label="Available" value={availabilityRatio} />
          <StatCard
            label="Unavailable"
            value={squad.injured + squad.suspended}
            delta={squad.injured > 0 ? `${squad.injured} injured` : undefined}
            deltaPositive={false}
          />
          <StatCard label="In doubt" value={squad.in_doubt} />
        </div>
      </div>

      <div className="stats--widget-divider" />

      <div className="stats-widget-row">
        <span className="stats-widget-row-lbl">This Season</span>
        <div className="stats-widget-cards">
          <StatCard
            label="Record"
            value={`${season.wins}W ${season.draws}D ${season.losses}L`}
          />
          <StatCard label="Goals scored" value={season.goals_scored} />
          <StatCard label="Goals conceded" value={season.goals_conceded} />
          <StatCard
            label="Win rate"
            value={`${winRate}`}
            delta={played > 0 ? `${played}` : "No games yet"}
          />
        </div>
      </div>
    </div>
  );
};
