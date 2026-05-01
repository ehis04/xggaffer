import { useState } from "react";
import type { QuestionProps } from "./types/QuizTypes";
import "./css/QuizQuestion.css";

export const TrueFalse = ({ question, onAnswerSelect, selectedAnswer }: QuestionProps) => {
    const [selectedId, setSelectedId] = useState<string | null>(null);

    const handleClick = (e: React.MouseEvent, value: "T" | "F") => {
        e.stopPropagation();
        setSelectedId(value);
        onAnswerSelect(question.id, value);
        setTimeout(() => setSelectedId(null), 300);
    };

    return (
        <div className="quiz-question-container">
            <div className="question-container"> <h2>{question.question}</h2></div>
            <p className="quiz-instruction">Choose an answer:</p>
            <div className="mcq-answers-container">
                {(["T", "F"] as const).map((value) => (
                    <div
                        key={value}
                        className={[
                            "quiz-answer",
                            selectedAnswer === value ? "selected" : "",
                            selectedId === value ? "animating" : "",
                        ].filter(Boolean).join(" ")}
                        onClick={(e) => handleClick(e, value)}
                    >
                        {value === "T" ? "True" : "False"}
                    </div>
                ))}
            </div>
        </div>
    );
};