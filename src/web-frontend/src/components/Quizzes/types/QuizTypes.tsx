export interface MCQOptionsData {
    id: number;
    answer: string;
    order: number;
}

export interface QuestionData {
    id: number;
    question_type: "TF" | "MC";
    question: string;
    mcq_options?: MCQOptionsData[];
    is_true_false: boolean;
    points: number;
}

export interface QuizData {
    id: number;
    title: string;
    description: string;
    difficulty: string;
    law_number: number;
    law_title: string;
    clause_heading: string;
    questions: QuestionData[];
}

export interface QuestionProps {
    question: QuestionData;
    onAnswerSelect: (questionId: number, answerId: number | string) => void;
    selectedAnswer?: number | string;
}

export interface QuizIdProps {
    quizId: number;
}

export interface ProgressBarProps {
    totalQuestions: number;
    selectedAnswers: Record<number, number | string>;
}