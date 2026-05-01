import "./css/DashboardCard.css";

export function StreakDay({
  label,
  studied,
  isToday,
}: {
  label: string;
  studied: boolean;
  isToday: boolean;
}) {
  const cls =
    "rdc-dot" + (isToday ? " rdc-dot--today" : studied ? " rdc-dot--done" : "");

  return (
    <div
      className="rdc-dot-group"
      aria-label={`${label}: ${studied || isToday ? "studied" : "no activity"}`}
    >
      <div className={cls} aria-hidden="true">
        {studied && !isToday && (
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="#3dd68c"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        )}
        {isToday && (
          <svg viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="5" fill="#3dd68c" />
          </svg>
        )}
      </div>
      <span
        className={`rdc-dot-label${isToday ? " rdc-dot-label--today" : ""}`}
      >
        {label}
      </span>
    </div>
  );
}
