import apiClient from "../../../services/api/client";
import { REFEREE } from "../../../services/api/endpoints";
import type { QuizData } from "../types/QuizTypes";

export const getQuizData = async (
  id: number,
  setQuizData: (quizData: QuizData) => void,
) => {
  try {
    const data = await apiClient.get<QuizData>(REFEREE.QUIZ_BY_ID(id));
    setQuizData(data);
  } catch (error) {
    console.error("Failed to fetch quiz:", error);
  }
};
