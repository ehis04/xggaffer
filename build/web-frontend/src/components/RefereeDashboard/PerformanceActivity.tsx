import type { PerformanceActivityData } from "./types/RefereeDashboardTypes";
import './css/PerformanceWidget.css';

export const PerformanceActivity = ({
  label,
  score,
  colour,
}: PerformanceActivityData) => {
  return (
    <div className="pa-row">
      <div className="pa-row-header">
        <span className="pa-row-lbl">{label}</span>
        <div className="pa-row-r">
          <span className="pa-row-score" style={{ color: colour }}>
            {score}%
          </span>
        </div>
      </div>
      <div
        className="pa-bar-track"
        role="progressbar"
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="pa-bar-fill"
          style={{ width: `${score}%`, background: colour }}
        />
      </div>
    </div>
  );
};
