import { MCQ } from "./MCQ";
import { TrueFalse } from "./TrueFalse";
import type { QuestionProps } from "./types/QuizTypes";
import "./css/QuizQuestion.css";

export const QuizQuestion = ({ question, onAnswerSelect, selectedAnswer }: QuestionProps) => {
    return (
        <div className="quizQs-container">
            {question.question_type === "MC" && (
                <MCQ
                    question={question}
                    onAnswerSelect={onAnswerSelect}
                    selectedAnswer={selectedAnswer}
                />
            )}
            {question.question_type === "TF" && (
                <TrueFalse
                    question={question}
                    onAnswerSelect={onAnswerSelect}
                    selectedAnswer={selectedAnswer}
                />
            )}
        </div>
    )
}