import { useParams } from "react-router-dom";
import { Quiz } from "../../components/Quizzes/Quiz";
import "./css/QuizPage.css";
import { Sidebar } from "../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import { SearchBar } from "../../components/Navigation/SearchBar";

export const QuizPage = () => {
  const { quizId } = useParams<{ quizId: string }>();

  return (
    <div className="quiz-page-container">
      <div className="sidebar-section">
        <Sidebar />
      </div>
      <div className="header-section">
        <SearchBar placeholder="Search" />
      </div>
      <div className="right-section">
        <div className="right-header">
          <SocialUserButtons />
        </div>
      </div>
      <div className="trendingBox-section"></div>
      <div className="main-section">
        <div className="quiz-content">
          <Quiz quizId={Number(quizId)} />
        </div>
      </div>
    </div>
  );
};
