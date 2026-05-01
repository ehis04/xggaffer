import type { ActiveProgressProps } from "./types/RefereeDashboardTypes";
import "../Quizzes/css/QuizProgressBar.css";

export const ActiveCourseProgress = ({ percentage }: ActiveProgressProps) => {
  return (
    <div className="progress-bar-container">
      <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
    </div>
  );
};
