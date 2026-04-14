import type {
  ActivityEvent,
  ActivityFeedWidgetProps,
} from "./types/DashboardTypes";
import { activityConfig } from "./functions/activityConfig";
import { formatRelativeTime } from "./functions/formatRelativeTime";
import "./css/ActivityFeedWidget.css";
import { ActivityEventDetail } from "./ActivityEventDetail";

export const ActivityFeedWidget = ({ events }: ActivityFeedWidgetProps) => {
  const recent = [...events]
    .sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    )
    .slice(0, 5);

    return (
        <div className="activity-feed">
            <div className="activity-feed-header">
                <span className="activity-feed-title"> Recent activity</span>
                <span className="activity-feed-count">{recent.length}</span>
            </div>

            <div className="activity-feed-list">
                {recent.length === 0 && (
                    <span className="activity-feed-empty"> No recent activity. </span>
                )}

                {recent.map((event, index) => {
                    const config = activityConfig[event.type]
                    const isLast = index === recent.length - 1

                    return (<ActivityEventDetail event={event} isLast={isLast}/>)
                })}
            </div>
        </div>
    )
};
