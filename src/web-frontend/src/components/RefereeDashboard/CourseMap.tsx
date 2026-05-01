import { CourseMapItem } from "./CourseMapItem";
import type { CourseMapProps } from "./types/RefereeDashboardTypes";
import './css/CourseMap.css';

export const CourseMap = ({ courses }: CourseMapProps) => {
  const safeCourses = courses ?? [];
  const completed = safeCourses.filter((c) => c.status === "completed").length;
  const total = safeCourses.length;

  return (
    <section className="cm" aria-label="Course Map">
      <div className="cm-header">
        <h2 className="cm-title">Course Map</h2>
        <span className="cm-tally">
          {completed}/{total} laws
        </span>
      </div>

      <ol className="cm-list">
        {safeCourses.map((course) => (
          <CourseMapItem key={course.law_number} course={course} />
        ))}
      </ol>
    </section>
  );
};
