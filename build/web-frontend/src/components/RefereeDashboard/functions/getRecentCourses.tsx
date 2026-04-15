import type { LawCourse } from "../types/RefereeDashboardTypes";

export function getRecentCourses(courses: LawCourse[]): LawCourse[] {
  return courses
    .filter((c) => c.status === "active" || c.status === "completed")
    .sort((a, b) => b.law_number - a.law_number)
    .slice(0, 3)
    .reverse();
}
 