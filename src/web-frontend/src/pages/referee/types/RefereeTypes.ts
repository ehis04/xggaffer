import type { ActiveCourse, LawCourse, StreakData, PerformanceData } from "../../../components/RefereeDashboard/types/RefereeDashboardTypes";
import type { CourseSection } from "../../../components/Courses/types/CourseTypes";

export interface DashboardData {
  active_course: ActiveCourse | null;
  courses:       LawCourse[];
  streak:        StreakData;
  performance:   PerformanceData;
}

export interface CourseResponse {
  law_number: number;
  law_title:  string;
  sections:   CourseSection[];
}