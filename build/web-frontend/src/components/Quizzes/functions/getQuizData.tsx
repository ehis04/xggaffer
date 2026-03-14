import { Api_Endpoints, authenticatedFetch } from "../../../services/api/AuthenticateUserApi";
import type { QuizData } from "../types/QuizTypes";

export const getQuizData = async (id: number, setQuizData: (quizData: QuizData) => void) => {
    try {
        const response = await authenticatedFetch(Api_Endpoints.GET_QUIZ(id), {
            method: "GET",
        })
        const data: QuizData = await response.json()
        setQuizData(data)
    } catch (error) {
        console.error("Failed to fetch quiz:", error)
    }
}