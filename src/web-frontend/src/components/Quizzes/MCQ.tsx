import { useState } from "react";
import type { QuestionProps } from "./types/QuizTypes";
import "./css/QuizQuestion.css";

export const MCQ = ({ question, onAnswerSelect, selectedAnswer }: QuestionProps) => {
    const [selectedId, setSelectedId] = useState<number | null>(null);

    const handleClick = (e: React.MouseEvent, optionId: number) => {
        e.stopPropagation();
        setSelectedId(optionId);
        onAnswerSelect(question.id, optionId);
        setTimeout(() => setSelectedId(null), 300);
    };

    return (
        <div className="quiz-question-container">
            <div className="question-container">
               <h2> {question.question} </h2>
            </div>
            <p className="quiz-instruction">Choose an answer:</p>
            <div className="mcq-answers-container">
                {question.mcq_options?.map((option) => (
                    <div
                        key={option.id}
                        className={[
                            "quiz-answer",
                            selectedAnswer === option.id ? "selected" : "",
                            selectedId === option.id ? "selected" : "",
                        ].filter(Boolean).join(" ")}
                        onClick={(e) => handleClick(e, option.id)}
                    >
                        <span className="answer-order-number"> {option.order} </span>{option.answer}
                    </div>
                ))}
            </div>
        </div>
    )
}