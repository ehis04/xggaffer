import { CompletedIcon } from "./CompletedIcon";
import { statusLabel } from "./functions/statusLabel";
import type { LawCourse } from "./types/RefereeDashboardTypes";
import './css/CourseMap.css';

export const CourseMapItem = ({course }: {course: LawCourse}) => {
    const canCLick = course.status !== "locked";

    const handleClick = () => {
        // if (canCLick) //navigate
    }

    return (
        <li className={`cmi cmi-${course.status}`}>
            <button className="cmi-btn" onClick={handleClick} disabled={!canCLick}>
                <div className={`cmi-num cmi-item-num-${course.status}`}>
                    <CompletedIcon status={course.status} />
                    {course.status !== "completed" && (
                        <span className="cmi-num">{course.law_number}</span>
                    )}
                </div>

                <div className="cmi-info">
                    <span className="cmi-title">{course.title}</span>
                    <span className="cmi-sub">
                        {course.status === "active" ? `${course.progress_percentage}% ${course.clauses_read}/${course.total_clauses} clauses` : statusLabel[course.status]}
                    </span>
                </div>
            </button>
        </li>
    )
}