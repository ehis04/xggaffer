import { formatDate, formatTime } from "./functions/calenderFuncs";
import { typeConfig } from "./functions/typeConfig";
import type { SessionEvent, SessionType } from "./types/DashboardTypes";
import './css/SessionWidget.css';

interface SessionRowProps {
  session: SessionEvent;
  config: (typeof typeConfig)[SessionType];
}

export const SessionRow = ({ session, config }: SessionRowProps) => {
  return (
    <button
      className="session-row"
      // onClick={() => navigate(`/coaching/sessions/${session.id}`)}
    >
      <div
        className="session-row-type-pill"
        style={{ color: config.colour, background: config.bg }}
      >
        {config.label}
      </div>

      <div className="session-row-info">
        <span className="session-row-title">{session.title}</span>
        <span className="session-row-meta">
          {formatDate(session.date)} {formatTime(session.date)}{" "}
          {session.duration_mins}mins
        </span>
      </div>

      <div className="session-row-attendance">
        <span className="session-row-attendance-count">
          {session.players_attended ?? "-"}/{session.total_players}
        </span>
        <span className="session-row-attendance-label">players</span>
      </div>
    </button>
  );
};
