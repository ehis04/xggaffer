import { useNavigate } from "react-router-dom";
import { ActiveCourseProgress } from "./ActiveCourseProgress";
import "./css/CourseCard.css";
import type {
  CourseStatus,
  LawCourseCardProps,
} from "./types/RefereeDashboardTypes";

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_LABEL: Record<CourseStatus, string> = {
  completed: "Complete",
  active: "In Progress",
  locked: "Locked",
};

function LockIcon() {
  return (
    <svg
      className="cc-lock-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      className="cc-check-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export const CourseCard = ({ course }: LawCourseCardProps) => {
  const navigate = useNavigate();
  const isInteractive = course.status !== "locked";

  const handleClick = () => {
    if (isInteractive) {
      navigate(`/referee/law/${course.law_number}`);
    }
  };

  return (
    <article
      className={`course-card-container course-card-container--${course.status}`}
      onClick={handleClick}
      role={isInteractive ? "button" : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      onKeyDown={(e) => e.key === "Enter" && handleClick()}
      aria-label={`Law ${course.law_number}: ${course.title} — ${STATUS_LABEL[course.status]}`}
      aria-disabled={!isInteractive}
    >
      <div className="course-card">

        {/* ── Front face ── */}
        <div className="course-card-front">

          {/* Top: law tag, title, description */}
          <div className="cc-front-top">
            <span className="cc-law-tag">Law {course.law_number}</span>
            <h3 className="cc-title">{course.title}</h3>
            <p className="cc-description">{course.description}</p>
          </div>

          {/* Bottom: progress bar + status badge */}
          <div className="cc-front-bottom">
            <div className="cc-bar-wrap">
              <div
                className="cc-bar-fill"
                style={{ width: `${course.progress_percentage}%` }}
              />
            </div>
            <span className={`cc-status-badge cc-status-badge--${course.status}`}>
              {course.status === "completed" && <CheckIcon />}
              {course.status === "locked" && <LockIcon />}
              {STATUS_LABEL[course.status]}
            </span>
          </div>

        </div>

        {/* ── Hover panel ── */}
        <div
          className={`course-card-hover course-card-hover--${course.status}`}
          aria-hidden="true"
        >
          <span className="cc-hover-law">Law {course.law_number}</span>
          <p className="cc-hover-title">{course.title}</p>

          {course.status === "locked" ? (
            <div className="cc-hover-locked">
              <LockIcon />
              <span>Complete the previous law to unlock</span>
            </div>
          ) : (
            <ActiveCourseProgress percentage={course.progress_percentage} />
          )}

          {course.status === "completed" && (
            <span className="cc-hover-complete-note">
              {course.clauses_read} / {course.total_clauses} clauses read
            </span>
          )}
        </div>

      </div>
    </article>
  );
};