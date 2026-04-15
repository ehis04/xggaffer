import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./App.css";

import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { PublicOnlyRoute } from "./components/auth/PublicOnlyRoute";

import LandingPage from "./pages/setup/LandingPage";
import ProfileCreationPage from "./pages/setup/ProfileCreationPage";
import { RoleAssignPage } from "./pages/setup/RoleAssignPage";
import { RoleProfilePage } from "./pages/setup/RoleProfilePage";
import { VerifyEmailPromptPage } from "./pages/setup/VerifyEmailPromptPage";
import { VerifyEmailCallbackPage } from "./pages/setup/VerifyEmailCallbackPage";

import { SocialPage } from './pages/social/SocialPage';
import { PostDetailPage } from './pages/social/PostDetailPage';

import RefBase from './pages/reffing/RefBase';
import QuizBase from './pages/reffing/quiz/QuizBase';
import ControlBase from './pages/reffing/controlTraining/ControlBase';
import ArticleBase from './pages/reffing/article/ArticleBase';
import FitnessBase from './pages/reffing/fitness/FitnessBase';
import SituationBase from './pages/reffing/situation/SituationBase';
import ChangesTimeline from './pages/reffing/quiz/ChangesTimeLine';
import LawDetail from './pages/reffing/quiz/LawDetails';
import LawsList from './pages/reffing/quiz/LawsList';

import { CoachingBase } from "./pages/coaching/CoachingBase";
import MyClubsPage from './pages/coaching/clubs/MyClubsPage';
import BrowseClubsPage from './pages/coaching/clubs/BrowseClubPage';
import CreateClubPage from './pages/coaching/clubs/CreateClubPage';
import ClubPlayersPage from './pages/coaching/clubs/ClubPlayersPage';
import { IndividualClubBase } from './pages/coaching/clubs/IndividualClubBase';
import TeamsheetDetail from "./pages/coaching/teamsheets/TeamsheetDetail";
import TeamsheetList from "./pages/coaching/teamsheets/TeamsheetList";
import TeamsheetListPage from "./pages/coaching/teamsheets/TeamsheetListPage";
import TeamsheetCreatePage from "./pages/coaching/teamsheets/TeamsheetCreatePage";
import TeamsheetDetailPage from "./pages/coaching/teamsheets/TeamsheetDetailPage";
import { UserProfilePage } from "./pages/user/UserProfilePage";
import { RefereeHome } from "./pages/referee/RefereeHome";
import { CoachingDashboard } from "./pages/coaching/CoachingDashboard";
import { CoursePage } from "./pages/referee/CoursePage";
import PredictionPage from './pages/predictions/PredictionPage';

import InternalPlayerProfilePage from './pages/coaching/playerdata/InternalPlayerProfilePage';
import InternalPlayerComparisonPage from './pages/coaching/playerdata/InternalPlayerComparisonPage';

import LiveFootballBasePage from './pages/livefootball/LiveFootballBasePage';
import LiveFootballPage from './pages/livefootball/LiveFootballPage';
import Leagues from './pages/livefootball/leagues/LeaguesPage';
import LeagueComparePage from './pages/livefootball/leagues/LeagueComparePage';
import LeagueCustomPage from './pages/livefootball/leagues/LeagueCustomPage';
import LeaguePredictPage from './pages/livefootball/leagues/LeaguePredictPage';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          <Route
            path="/"
            element={
              <PublicOnlyRoute redirectTo="/social" useFrom={false}>
                <LandingPage />
              </PublicOnlyRoute>
            }
          />

          <Route path="/verify-email/confirm" element={<VerifyEmailCallbackPage />} />

          <Route element={<ProtectedRoute requireVerified={false} />}>
            <Route path="/verify-email" element={<VerifyEmailPromptPage />} />
            <Route path="/create/profile" element={<ProfileCreationPage />} />
            <Route path="/create/profile/role" element={<RoleAssignPage />} />
            <Route
              path="/create/profile/role/details"
              element={<RoleProfilePage />}
            />
          </Route>
          <Route path="/profile/:username" element={<UserProfilePage />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/social" element={<SocialPage />} />
            <Route path="/social/post/:postId" element={<PostDetailPage />} />

            <Route path="/refbase" element={<RefBase />} />
            <Route path="/quizbase" element={<QuizBase />} />
            <Route path="/controlBase" element={<ControlBase />} />
            <Route path="/articleBase" element={<ArticleBase />} />
            <Route path="/fitnessBase" element={<FitnessBase />} />
            <Route path="/situationBase" element={<SituationBase />} />
            <Route path="/referee/" element={<RefereeHome />} />
            <Route path="/referee/law/:lawNumber" element={<CoursePage />} />

            <Route path="/coaching" element={<CoachingBase />} />
            <Route path="/coaching/teamsheets" element={<TeamsheetList />} />
            <Route
              path="/coaching/teamsheets/:id"
              element={<TeamsheetDetail />}
            />
            <Route path="/coaching/predictions" element={<PredictionPage />} />

            <Route path="/coaching/playerdata" element={<InternalPlayerProfilePage />} />
            <Route path="/coaching/playerdata/player" element={<InternalPlayerProfilePage />} />
            <Route path="/coaching/playerdata/player/:playerId" element={<InternalPlayerProfilePage />} />
            <Route path="/coaching/playerdata/compare" element={<InternalPlayerComparisonPage />} />
            <Route path="/livefootball" element={<LiveFootballBasePage />} />
            <Route path="/livefootball/competitions" element={<LiveFootballPage />} />
            <Route path="/livefootball/leagues" element={<Leagues />} />
            <Route path="/livefootball/leagues/compare" element={<LeagueComparePage />} />
            <Route path="/livefootball/leagues/custom" element={<LeagueCustomPage />} />
            <Route path="/livefootball/leagues/predict" element={<LeaguePredictPage />} />


            <Route path="/clubs" element={<MyClubsPage />} />
            <Route path="/clubs/browse" element={<BrowseClubsPage />} />
            <Route path="/clubs/create" element={<CreateClubPage />} />
            <Route
              path="/clubs/:clubId/teamsheets"
              element={<TeamsheetListPage />}
            />
            <Route
              path="/clubs/:clubId/teamsheets/new"
              element={<TeamsheetCreatePage />}
            />
            <Route
              path="/clubs/:clubId/teamsheets/:teamsheetId"
              element={<TeamsheetDetailPage />}
            />
            <Route path="/coaching/dashboard" element={<CoachingDashboard />} />
            <Route path="/clubs/:clubId/" element={<IndividualClubBase />} />
            <Route path="/clubs/:clubId/players" element={<ClubPlayersPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
          

          
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;