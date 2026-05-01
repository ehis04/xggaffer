import { getWeekDates, isSameDay } from "./functions/calenderFuncs";
import { typeConfig } from "./functions/typeConfig";
import { SessionRow } from "./SessionRow";
import { SessionWeek } from "./SessionWeek";
import type { SessionWidgetProps } from "./types/DashboardTypes";
import './css/SessionWidget.css';

export const SessionWidget = ({ sessions }: SessionWidgetProps) => {
  const weekDates = getWeekDates();
  const today = new Date();

  const upcoming = sessions
    .filter((s) => new Date(s.date) >= today)
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    .slice(0, 5);

  return (
    <div className="session-widget">
      <div className="session-week">
        {weekDates.map((date, i) => {
          const isToday = isSameDay(date, today);
          const dayEvents = sessions.filter((s) =>
            isSameDay(new Date(s.date), date),
          );
          return (
            <SessionWeek
              key={date.toISOString()}
              i={i}
              isToday={isToday}
              date={date}
              dayEvents={dayEvents}
            />
          );
        })}
      </div>

      <div className="session-widget-divider" />

      <div className="session-list">
        <span className="session-list-heading">Upcoming</span>

        {upcoming.length === 0 && (
          <span className="session-list-empty">
            Nothing has been scheduled.
          </span>
        )}

        {upcoming.map((session) => {
          const config = typeConfig[session.type];

          return <SessionRow key={session.id} session={session} config={config} />;
        })}
      </div>
    </div>
  );
};
