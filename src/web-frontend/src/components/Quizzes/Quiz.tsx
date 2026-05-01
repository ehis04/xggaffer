import { useEffect, useState } from "react";
import { QuizQuestion } from "./QuizQuestion";
import type { QuizData, QuizIdProps } from "./types/QuizTypes";
import { getQuizData } from "./functions/getQuizData";
import "./css/QuizQuestion.css";
import { QuizProgressBar } from "./QuizProgressBar";

export const Quiz = ({ quizId }: QuizIdProps) => {
  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [selectedAnswers, setSelectedAnswers] = useState<
    Record<number, number | string>
  >({});
  const [currQuestion, setCurrQuestion] = useState(0);

  useEffect(() => {
    getQuizData(quizId, setQuiz);
  }, [quizId]);

  if (!quiz) return <div>Loading quiz</div>;

  const handleAnswerSelect = (
    questionId: number,
    answerId: number | string,
  ) => {
    setSelectedAnswers((prev) => ({
      ...prev,
      [questionId]: answerId,
    }));
  };

  const handleNextQuestion = () => {
    if (currQuestion < quiz.questions.length - 1) {
      setCurrQuestion((prev) => prev + 1);
    }
  };

  const handlePrevQuestion = () => {
    if (currQuestion > 0) {
      setCurrQuestion((prev) => prev - 1);
    }
  };

  const submitQuiz = () => {
    /* add quiz submission logic */
  };

  const currentQuestion = quiz.questions[currQuestion];
  const isLastQuestion = currQuestion === quiz.questions.length - 1;

  return (
    <div className="quiz-container">
      <div className="quiz-title-container">
        <h2 className="quiz-title">{quiz.title}</h2>
      </div>

      <p className="question-number-index">
        <span className="active-q">Question {currQuestion + 1}</span> of{" "}
        {quiz.questions.length}
      </p>
      <QuizProgressBar totalQuestions={quiz.questions.length} selectedAnswers={selectedAnswers} />

      <div className="quiz-questions-container">
        <QuizQuestion
          key={currentQuestion.id}
          question={currentQuestion}
          onAnswerSelect={handleAnswerSelect}
          selectedAnswer={selectedAnswers[currentQuestion.id]}
        />
      </div>

      <div className="navigation-buttons">
        <button
          className="quiz-nav-button"
          onClick={handlePrevQuestion}
          disabled={currQuestion === 0}
        >
          Previous
        </button>

        {isLastQuestion ? (
          <button className="quiz-submit-button" onClick={submitQuiz}>
            Submit
          </button>
        ) : (
          <button className="quiz-nav-button" onClick={handleNextQuestion}>
            Next
          </button>
        )}
      </div>
    </div>
  );
};
