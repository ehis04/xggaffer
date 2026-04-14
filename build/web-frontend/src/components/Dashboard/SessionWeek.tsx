import { typeConfig } from "./functions/typeConfig";
import './css/SessionWidget.css';
import { dayLabels } from "./functions/dayLabels";

export const SessionWeek = ({ i, isToday, date, dayEvents }) => {
  return (
    <div
      key={i}
      className={`session-week-day ${isToday ? "session-week-day--today" : ""}`}
    >
      <span className="session-week-lbl">{dayLabels[i]}</span>
      <span className="session-week-date">{date.getDate()}</span>
      <div className="session-week-dots">
        {dayEvents.map((event) => (
          <span
            key={event.id}
            className="session-week-dot"
            style={{ background: typeConfig[event.type].colour }}
            title={typeConfig[event.type].label}
          />
        ))}
      </div>
    </div>
  );
};
