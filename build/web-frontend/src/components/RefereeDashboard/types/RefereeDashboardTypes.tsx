export interface ActiveCourse {
  law_number: number;
  title: string;
  progress_percentage: number;
  clauses_read: number;
  total_clauses: number;
}

export interface StreakData {
  current_streak: number;
  studied_dates: string[];
}

export interface RefereeDashboardCardProps {
  activeCourse?: ActiveCourse | null;
  streak?: StreakData;
}

export interface ActiveProgressProps {
  percentage: number;
}

export type CourseStatus = "completed" | "active" | "locked";
 
export interface LawCourse {
  law_number: number;
  title: string;
  description: string;
  status: CourseStatus;
  progress_percentage: number;
  clauses_read: number;
  total_clauses: number;
}
 
export interface LawCourseCardProps {
  course: LawCourse;
}

export interface YourCoursesProps {
  courses?: LawCourse[];
}

export interface ActivityScore {
  score: number;
}

export interface PerformanceData {
  overall_score: number;
  quizzes?: ActivityScore;
  scenarios?: ActivityScore;
  drills?: ActivityScore;
  clauses?: ActivityScore;
}

export interface PerformanceWidgetProps {
  data: PerformanceData;
}

export interface PerformanceActivityData {
  label: string;
  score: number;
  colour: string;
}

export interface CourseMapProps {
  courses?: LawCourse[];
}