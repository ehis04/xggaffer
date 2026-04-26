import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";

import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { PublicOnlyRoute } from "./components/auth/PublicOnlyRoute";
import { RouteErrorBoundary } from "./pages/status/RouteErrorBoundary";
import { NotFoundPage } from "./pages/status/NotFoundPage";

import LandingPage from "./pages/setup/LandingPage";
import ProfileCreationPage from "./pages/setup/ProfileCreationPage";
import { RoleAssignPage } from "./pages/setup/RoleAssignPage";
import { RoleProfilePage } from "./pages/setup/RoleProfilePage";
import { VerifyEmailPromptPage } from "./pages/setup/VerifyEmailPromptPage";
import { VerifyEmailCallbackPage } from "./pages/setup/VerifyEmailCallbackPage";
import { ForgotPasswordPage } from "./pages/setup/ForgotPasswordPage";
import { ResetPasswordPage } from "./pages/setup/ResetPasswordPage";

import { SocialPage } from "./pages/social/SocialPage";
import { PostDetailPage } from "./pages/social/PostDetailPage";

import RefBase from "./pages/reffing/RefBase";
import QuizBase from "./pages/reffing/quiz/QuizBase";
import ControlBase from "./pages/reffing/controlTraining/ControlBase";
import ArticleBase from "./pages/reffing/article/ArticleBase";
import FitnessBase from "./pages/reffing/fitness/FitnessBase";
import SituationBase from "./pages/reffing/situation/SituationBase";
import ChangesTimeline from "./pages/reffing/quiz/ChangesTimeLine";
import LawDetail from "./pages/reffing/quiz/LawDetails";
import LawsList from "./pages/reffing/quiz/LawsList";
import TrashPage from "./pages/social/TrashPage";

import { CoachingBase } from "./pages/coaching/CoachingBase";
import MyClubsPage from "./pages/coaching/clubs/MyClubsPage";
import BrowseClubsPage from "./pages/coaching/clubs/BrowseClubPage";
import CreateClubPage from "./pages/coaching/clubs/CreateClubPage";
import ClubPlayersPage from "./pages/coaching/clubs/ClubPlayersPage";
import { IndividualClubBase } from "./pages/coaching/clubs/IndividualClubBase";
import { UserProfilePage } from "./pages/user/UserProfilePage";
import { RefereeHome } from "./pages/referee/RefereeHome";
import { CoursePage } from "./pages/referee/CoursePage";
import TeamsheetCreatePage from "./pages/coaching/teamsheets/TeamsheetCreatePage";
import TeamsheetDetailPage from "./pages/coaching/teamsheets/TeamsheetDetailPage";
import TeamsheetEditPage from "./pages/coaching/teamsheets/TeamsheetEditPage";
import TeamsheetListPage from "./pages/coaching/teamsheets/TeamsheetListPage";
import TacticsBoardListPage from "./pages/coaching/tactics/TacticsBoardListPage";
import PredictionPage from "./pages/predictions/PredictionPage";
import InternalPlayerProfilePage from "./pages/coaching/playerdata/InternalPlayerProfilePage";
import InternalPlayerComparisonPage from "./pages/coaching/playerdata/InternalPlayerComparisonPage";

import LiveFootballBasePage from "./pages/livefootball/LiveFootballBasePage";
import LiveFootballPage from "./pages/livefootball/LiveFootballPage";
import Leagues from "./pages/livefootball/leagues/LeaguesPage";
import LeagueComparePage from "./pages/livefootball/leagues/LeagueComparePage";
import LeagueCustomPage from "./pages/livefootball/leagues/LeagueCustomPage";
import LeaguePredictPage from "./pages/livefootball/leagues/LeaguePredictPage";

import OddsComparisonPage from "./pages/predictions/OddsComparisonPage";
import PredictionsHub from "./pages/predictions/PredictionsHub";
import SeasonProjectionCentre from "./pages/predictions/SeasonProjectionCentre";

import TacticsBoardEditorPage from "./pages/coaching/tactics/TacticsBoardEditorPage";
import AuthenticatedLayout from "./utils/AuthenticatedLayout";
import ArticlesPage from "./pages/articles/ArticlesPage";
import ArticleDetailPage from "./pages/articles/ArticleDetailPage";

import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './common/query/queryClient';
import { ClubDetailsPage } from "./pages/coaching/clubs/ClubDetails";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app">
        <RouteErrorBoundary>
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
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route element={<ProtectedRoute requireVerified={false} />}>
              <Route path="/verify-email" element={<VerifyEmailPromptPage />} />
              <Route path="/create/profile" element={<ProfileCreationPage />} />
              <Route path="/create/profile/role" element={<RoleAssignPage />} />
              <Route path="/create/profile/role/details" element={<RoleProfilePage />} />
            </Route>

            <Route path="/profile/:username" element={<UserProfilePage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AuthenticatedLayout />}>
                <Route path="/social" element={<SocialPage />} />
                <Route path="/articles" element={<ArticlesPage />} />
                <Route path="/articles/:articleId" element={<ArticleDetailPage />} />
                <Route path="/social/post/:postId" element={<PostDetailPage />} />
                <Route path="/trash" element={<TrashPage />} />
                <Route path="/refbase" element={<RefBase />} />
                <Route path="/quizbase" element={<QuizBase />} />
                <Route path="/controlBase" element={<ControlBase />} />
                <Route path="/articleBase" element={<ArticleBase />} />
                <Route path="/fitnessBase" element={<FitnessBase />} />
                <Route path="/situationBase" element={<SituationBase />} />
                <Route path="/laws" element={<LawsList />} />
                <Route path="/laws/:lawNumber" element={<LawDetail />} />
                <Route path="/laws/changes" element={<ChangesTimeline />} />
                <Route path="/referee/" element={<RefereeHome />} />
                <Route path="/referee/law/:lawNumber" element={<CoursePage />} />
                <Route path="/coaching" element={<CoachingBase />} />
                <Route path="/coaching/clubs/create" element={<CreateClubPage />} />
                <Route path="/coaching/predictions" element={<PredictionPage />} />
                <Route path="/predictions/hub" element={<PredictionsHub />} />
                <Route path="/coaching/predictions/odds" element={<OddsComparisonPage />} />
                <Route path="/coaching/playerdata/player" element={<InternalPlayerProfilePage />} />
                <Route path="/coaching/playerdata/compare" element={<InternalPlayerComparisonPage />} />
                <Route path="/season/:leagueCode" element={<SeasonProjectionCentre />} />
                <Route path="/livefootball" element={<LiveFootballBasePage />} />
                <Route path="/livefootball/competitions" element={<LiveFootballPage />} />
                <Route path="/livefootball/leagues" element={<Leagues />} />
                <Route path="/livefootball/leagues/compare" element={<LeagueComparePage />} />
                <Route path="/livefootball/leagues/custom" element={<LeagueCustomPage />} />
                <Route path="/livefootball/leagues/predict" element={<LeaguePredictPage />} />
                <Route path="/clubs" element={<MyClubsPage />} />
                <Route path="/clubs/browse" element={<BrowseClubsPage />} />
                <Route path="/clubs/:clubId/teamsheets/:teamsheetId" element={<TeamsheetDetailPage />} />
                <Route path="/clubs/:clubId/teamsheets" element={<TeamsheetListPage />} />
                <Route path="/clubs/:clubId/teamsheets/new" element={<TeamsheetCreatePage />} />
                <Route path="/clubs/:clubId/teamsheets/:teamsheetId/edit" element={<TeamsheetEditPage />} />
                <Route path="/clubs/:clubId/" element={<IndividualClubBase />} />
                <Route path="/clubs/:clubId/details" element={<ClubDetailsPage />} />
                <Route path="/clubs/:clubId/players" element={<ClubPlayersPage />} />
                <Route path="/clubs/:clubId/tactics-boards" element={<TacticsBoardListPage />} />
                <Route path="/clubs/:clubId/tactics-boards/:boardId" element={<TacticsBoardEditorPage />} />
              </Route>
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </RouteErrorBoundary>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;