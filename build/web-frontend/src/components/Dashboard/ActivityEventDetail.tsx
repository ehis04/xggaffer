import "./css/ActivityFeedWidget.css";
import { formatRelativeTime } from "./functions/formatRelativeTime";

export const ActivityEventDetail = ({event, isLast}) => {
    return (
        <div key={event.id} className={`activity-row ${isLast ? 'activity-row-last' : ''}`}>
            <div className="activity-row-timeline">
                {!isLast && <div className="activity-row-line"/>}
            </div>

            <div className="activity-row-content">
                <div className="activity-row-top">
                    <span className="activity-row-title">{event.title}</span>
                    <span className="activity-row-time"> {formatRelativeTime(event.timestamp)}</span>
                </div>
                <span className="activity-row-detail">{event.detail}</span>
            </div>
        </div>
    )
}