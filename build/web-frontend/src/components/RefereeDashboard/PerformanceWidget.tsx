import { activities } from "./functions/activities";
import { PerformanceActivity } from "./PerformanceActivity";
import { PerformanceRing } from "./PerformanceRing";
import type { ActivityScore, PerformanceWidgetProps } from "./types/RefereeDashboardTypes";
import './css/PerformanceWidget.css';

export const PerformanceWidget = ({data}: PerformanceWidgetProps) => {
    return <section className="pw" aria-label="Performance">
        <PerformanceRing score={data.overall_score} />
        <div className="pw-divider" aria-hidden="true" />

        <div className="pw-rows">
            {activities.map(({key, label, colour}) => {
                const activity = data[key] as ActivityScore;
                if (!activity) return null;
                
                return (
                    <PerformanceActivity key={key} label={label} score={activity.score} colour={colour} />
                )
            })}
        </div>
    </section>
}