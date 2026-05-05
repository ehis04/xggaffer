import type { ProgressBarProps } from "./types/QuizTypes";
import "./css/QuizProgressBar.css";

export const QuizProgressBar = ({
  totalQuestions,
  selectedAnswers,
}: ProgressBarProps) => {
  const answered = Object.keys(selectedAnswers).length;
  const percentage = Math.round((answered / totalQuestions) * 100);

  return (
    <div className="progress-bar-container">
      <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
    </div>
  );
};
