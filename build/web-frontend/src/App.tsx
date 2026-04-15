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
import { ForgotPasswordPage } from "./pages/setup/ForgotPasswordPage";
import { ResetPasswordPage } from "./pages/setup/ResetPasswordPage";

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
import TrashPage from './pages/social/TrashPage';

import { CoachingBase } from "./pages/coaching/CoachingBase";
import MyClubsPage from './pages/coaching/clubs/MyClubsPage';
import BrowseClubsPage from './pages/coaching/clubs/BrowseClubPage';
import CreateClubPage from './pages/coaching/clubs/CreateClubPage';
import ClubPlayersPage from './pages/coaching/clubs/ClubPlayersPage';
import { IndividualClubBase } from "./pages/coaching/clubs/IndividualClubBase";
import { UserProfilePage } from "./pages/user/UserProfilePage";
import { RefereeHome } from "./pages/referee/RefereeHome";
import { CoachingDashboard } from "./pages/coaching/CoachingDashboard";
import { CoursePage } from "./pages/referee/CoursePage";
import TeamsheetDetail from "./pages/coaching/teamsheets/TeamsheetDetail";
import TeamsheetList from "./pages/coaching/teamsheets/TeamsheetList";
import TeamsheetListPage from "./pages/coaching/teamsheets/TeamsheetListPage";
import TeamsheetCreatePage from "./pages/coaching/teamsheets/TeamsheetCreatePage";
import TeamsheetDetailPage from "./pages/coaching/teamsheets/TeamsheetDetailPage";
import TeamsheetEditPage from "./pages/coaching/teamsheets/TeamsheetEditPage";
import PredictionPage from "./pages/predictions/PredictionPage";

import InternalPlayerProfilePage from "./pages/coaching/playerdata/InternalPlayerProfilePage";
import InternalPlayerComparisonPage from "./pages/coaching/playerdata/InternalPlayerComparisonPage";

import LiveFootballBasePage from "./pages/livefootball/LiveFootballBasePage";
import LiveFootballPage from "./pages/livefootball/LiveFootballPage";
import Leagues from "./pages/livefootball/leagues/LeaguesPage";
import LeagueComparePage from "./pages/livefootball/leagues/LeagueComparePage";
import LeagueCustomPage from "./pages/livefootball/leagues/LeagueCustomPage";
import LeaguePredictPage from "./pages/livefootball/leagues/LeaguePredictPage";

import TacticsBoardListPage from "./pages/coaching/tactics/TacticsBoardListPage";
import TacticsBoardEditorPage from "./pages/coaching/tactics/TacticsBoardEditorPage";

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          /* no issue */
          <Route
            path="/"
            element={
              <PublicOnlyRoute redirectTo="/social" useFrom={false}>
                <LandingPage />
              </PublicOnlyRoute>
            }
          />
           /* working fine */
          <Route path="/verify-email/confirm" element={<VerifyEmailCallbackPage />} />
          /* working fine */
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          /* working fine */
          <Route path="/reset-password" element={<ResetPasswordPage />} />

          <Route element={<ProtectedRoute requireVerified={false} />}>
            /* working fine */
            <Route path="/verify-email" element={<VerifyEmailPromptPage />} />
            /* working fine */
            <Route path="/create/profile" element={<ProfileCreationPage />} />
            /* working fine */
            <Route path="/create/profile/role" element={<RoleAssignPage />} />
            <Route
              path="/create/profile/role/details"
              element={<RoleProfilePage />}
            />
          </Route>
          <Route path="/profile/:username" element={<UserProfilePage />} />

          <Route element={<ProtectedRoute />}>
            /* need lizzy push */
            <Route path="/social" element={<SocialPage />} />
            /* need lizzy push */
            <Route path="/social/post/:postId" element={<PostDetailPage />} />
            /* working fine */
            <Route path="/trash" element={<TrashPage />} />

            /* need to see lizzy push */
            <Route path="/refbase" element={<RefBase />} />
            /* need to see lizzy push */
            <Route path="/quizbase" element={<QuizBase />} />
            /* probably going to bin */
            <Route path="/controlBase" element={<ControlBase />} />
            /* need to review backend, probably going to assimilated into social page */
            <Route path="/articleBase" element={<ArticleBase />} />
            /* need to see lizzy push */
            <Route path="/fitnessBase" element={<FitnessBase />} />
            /* need to see lizzy push */
            <Route path="/situationBase" element={<SituationBase />} />
            <Route path="/laws" element={<LawsList />} />
            <Route path="/laws/:lawNumber" element={<LawDetail />} />
            <Route path="/laws/changes" element={<ChangesTimeline />} />
            <Route path="/referee/" element={<RefereeHome />} />
            <Route path="/referee/law/:lawNumber" element={<CoursePage />} />

            <Route path="/coaching" element={<CoachingBase />} />

            /* old page, delete */
            <Route path="/coaching/teamsheets" element={<TeamsheetList />} />
            <Route
              path="/coaching/teamsheets/:id"
              element={<TeamsheetDetail />}
            />
            <Route path="/coaching/predictions" element={<PredictionPage />} />

            /* no issues, upgrades noted in docs */
            <Route path="/coaching/playerdata/player" element={<InternalPlayerProfilePage />} />
            /* no issues, upgrades noted in docs */
            <Route path="/coaching/playerdata/compare" element={<InternalPlayerComparisonPage />} />
            /* no issues, upgrades noted in docs */
            <Route path="/livefootball" element={<LiveFootballBasePage />} />
            /* old page, to be deleted */
            <Route path="/livefootball/competitions" element={<LiveFootballPage />} />
            /* no issues, upgrades noted in docs */
            <Route path="/livefootball/leagues" element={<Leagues />} />
            /* no issues, upgrades noted in docs */
            <Route path="/livefootball/leagues/compare" element={<LeagueComparePage />} />
            /* come back */
            <Route path="/livefootball/leagues/custom" element={<LeagueCustomPage />} />
            /* no issues, upgrades noted in docs */
            <Route path="/livefootball/leagues/predict" element={<LeaguePredictPage />} />

            /* no issues */
            <Route path="/clubs" element={<MyClubsPage />} />

            /* change in process*/
            <Route path="/clubs/browse" element={<BrowseClubsPage />} />

            /* no issues, upgrades noted in docs */
            <Route
              path="/clubs/:clubId/teamsheets/:teamsheetId"
              element={<TeamsheetDetailPage />}
            />
            <Route path="/coaching/dashboard" element={<CoachingDashboard />} />

            /* no issues, upgrades noted in docs
            */

            <Route
              path="/clubs/:clubId/teamsheets"
              element={<TeamsheetListPage />}
            />

            /* no issues here, upgrades noted in docs */
            <Route
              path="/clubs/:clubId/teamsheets/new"
              element={<TeamsheetCreatePage />}
            />

            /* no issues, upgrades noted in docs */
            <Route
              path="/clubs/:clubId/teamsheets/:teamsheetId"
              element={<TeamsheetDetailPage />}
            />
            <Route path="/coaching/dashboard" element={<CoachingDashboard />} />

            /* No issues, updates noted in docs*/
            <Route path="/clubs/:clubId/teamsheets/:teamsheetId/edit" element={<TeamsheetEditPage />} />
            <Route path="/coaching/dashboard" element={<CoachingDashboard />} />

            <Route path="/clubs/:clubId/" element={<IndividualClubBase />} />
            <Route path="/clubs/:clubId/players" element={<ClubPlayersPage />} />

            <Route path="/clubs/:clubId/tactics-boards" element={<TacticsBoardListPage />} />
            <Route path="/clubs/:clubId/tactics-boards/:boardId" element={<TacticsBoardEditorPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
          

          
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;