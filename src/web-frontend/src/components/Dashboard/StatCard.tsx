import type { StatCardProps } from "./types/DashboardTypes";
import './css/StatsWidget.css';

export const StatCard = ({label, value, delta, deltaPositive}: StatCardProps) => (
    <div className="stat-card">
        <span className="stat-card-label">{label}</span>
        <span className="stat-card-value">{value}</span>
        {delta && (
            <span className={`stat-card-delta ${deltaPositive ? "stat-card-delta--up" : "stat-card-delta--down"}`}>
                {delta}
            </span>
        )}
    </div>
)