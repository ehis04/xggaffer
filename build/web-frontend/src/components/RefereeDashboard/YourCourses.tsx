import { CourseCard } from "./CourseCard";
import "./css/YourCourses.css";
import { getRecentCourses } from "./functions/getRecentCourses";
import type { YourCoursesProps } from "./types/RefereeDashboardTypes";

export const YourCourses = ({ courses }: YourCoursesProps) => {
  const recentCourses = getRecentCourses(courses);

  return (
    <div className="yc-container">
      <div className="yc-header">
        <span className="yc-title">Your Courses</span>
        <span className="yc-header-right"> view all →</span>
      </div>
      <div className="yc-grid">
        {recentCourses.map((course) => (
          <CourseCard key={course.law_number} course={course} />
        ))}
      </div>
    </div>
  );
};
