// --- Framework & Core ---
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import "./App.css";

// --- Query Client ---
import { queryClient } from "./common/query/queryClient";

// --- Route Guards & Layout ---
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { PublicOnlyRoute } from "./components/auth/PublicOnlyRoute";
import { RouteErrorBoundary } from "./pages/status/RouteErrorBoundary";
import { NotFoundPage } from "./pages/status/NotFoundPage";
import AuthenticatedLayout from "./utils/AuthenticatedLayout";

// --- Account Registration & Auth Flow ---
import LandingPage from "./pages/setup/LandingPage";
import ProfileCreationPage from "./pages/setup/ProfileCreationPage";
import { RoleAssignPage } from "./pages/setup/RoleAssignPage";
import { RoleProfilePage } from "./pages/setup/RoleProfilePage";
import { VerifyEmailPromptPage } from "./pages/setup/VerifyEmailPromptPage";
import { VerifyEmailCallbackPage } from "./pages/setup/VerifyEmailCallbackPage";
import { ForgotPasswordPage } from "./pages/setup/ForgotPasswordPage";
import { ResetPasswordPage } from "./pages/setup/ResetPasswordPage";

// --- User Profile ---
import { UserProfilePage } from "./pages/user/UserProfilePage";

// --- Social Feed ---
import { SocialPage } from "./pages/social/SocialPage";
import { PostDetailPage } from "./pages/social/PostDetailPage";
import TrashPage from "./pages/social/TrashPage";

// --- Articles ---
import ArticlesPage from "./pages/articles/ArticlesPage";
import FavouriteArticlesPage from "./pages/articles/FavouriteArticlesPage";
import ArticleDetailPage from "./pages/articles/ArticleDetailPage";
import ArticleProfilePage from "./pages/articles/ArticleProfilePage";

// --- Refereeing & Laws ---
import { RefereeHome } from "./pages/referee/RefereeHome";
import { CoursePage } from "./pages/referee/CoursePage";

// --- Coaching & Clubs ---
import { CoachingBase } from "./pages/coaching/CoachingBase";
import MyClubsPage from "./pages/coaching/clubs/MyClubsPage";
import BrowseClubsPage from "./pages/coaching/clubs/BrowseClubPage";
import CreateClubPage from "./pages/coaching/clubs/CreateClubPage";
import { IndividualClubBase } from "./pages/coaching/clubs/IndividualClubBase";
import TeamsheetCreatePage from "./pages/coaching/teamsheets/TeamsheetCreatePage";
import TeamsheetDetailPage from "./pages/coaching/teamsheets/TeamsheetDetailPage";
import TeamsheetEditPage from "./pages/coaching/teamsheets/TeamsheetEditPage";
import TeamsheetListPage from "./pages/coaching/teamsheets/TeamsheetListPage";

import TacticsBoardEditorPage from "./pages/coaching/tactics/TacticsBoardEditorPage";
import InternalPlayerProfilePage from "./pages/coaching/playerdata/InternalPlayerProfilePage";
import InternalPlayerComparisonPage from "./pages/coaching/playerdata/InternalPlayerComparisonPage";

// --- Predictions & Intelligence ---
import PredictionPage from "./pages/predictions/PredictionPage";
import OddsComparisonPage from "./pages/predictions/OddsComparisonPage";
import PredictionsHub from "./pages/predictions/PredictionsHub";
import SeasonProjectionCentre from "./pages/predictions/SeasonProjectionCentre";
import MatchIntelligenceHub from "./pages/predictions/MatchIntelligenceHub";
import TacticalScoutingDashboard from "./pages/predictions/TacticalScoutingDashboard";
import SquadIntelligenceHub from "./pages/predictions/SquadIntelligenceHub";
import ModelTrustCentre from "./pages/predictions/ModelTrustCentre";

// --- Live Football ---
import LiveFootballBasePage from "./pages/livefootball/LiveFootballBasePage";
import Leagues from "./pages/livefootball/leagues/LeaguesPage";
import LeagueComparePage from "./pages/livefootball/leagues/LeagueComparePage";
import LeagueCustomPage from "./pages/livefootball/leagues/LeagueCustomPage";
import LeaguePredictPage from "./pages/livefootball/leagues/LeaguePredictPage";
import { ClubDetailsPage } from "./pages/coaching/clubs/ClubDetails";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app">
          <RouteErrorBoundary>
            <Routes>

              {/* --- Unprotected Routes: Account Registration & Auth Flow --- */}
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

              {/* --- Authenticated (unverified) Routes: Profile Setup Flow --- */}
              <Route element={<ProtectedRoute requireVerified={false} />}>
                <Route path="/verify-email" element={<VerifyEmailPromptPage />} />
                <Route path="/create/profile" element={<ProfileCreationPage />} />
                <Route path="/create/profile/role" element={<RoleAssignPage />} />
                <Route path="/create/profile/role/details" element={<RoleProfilePage />} />
              </Route>

              {/* --- Semi-public Route: User Profile --- */}
              <Route path="/profile/:username" element={<UserProfilePage />} />

              {/* === Protected Routes (verified users) === */}
              <Route element={<ProtectedRoute />}>
                <Route element={<AuthenticatedLayout />}>

                  {/* --- Social Feed --- */}
                  <Route path="/social" element={<SocialPage />} />
                  <Route path="/social/post/:postId" element={<PostDetailPage />} />
                  <Route path="/trash" element={<TrashPage />} />

                  {/* --- Articles --- */}
                  <Route path="/articles" element={<ArticlesPage />} />
                  <Route path="/articles/favourites" element={<FavouriteArticlesPage />} />
                  <Route path="/articles/profile" element={<ArticleProfilePage />} />
                  <Route path="/articles/:articleId" element={<ArticleDetailPage />} />

                  {/* --- Refereeing & Laws --- */}
                  <Route path="/referee/" element={<RefereeHome />} />
                  <Route path="/referee/law/:lawNumber" element={<CoursePage />} />

                  {/* --- Coaching & Clubs --- */}
                  <Route path="/coaching" element={<CoachingBase />} />
                  <Route path="/coaching/clubs/create" element={<CreateClubPage />} />
                  <Route path="/clubs" element={<MyClubsPage />} />
                  <Route path="/clubs/browse" element={<BrowseClubsPage />} />
                  <Route path="/clubs/:clubId/" element={<IndividualClubBase />} />
                  <Route path="/clubs/:clubId/teamsheets" element={<TeamsheetListPage />} />
                  <Route path="/clubs/:clubId/teamsheets/new" element={<TeamsheetCreatePage />} />
                  <Route path="/clubs/:clubId/teamsheets/:teamsheetId" element={<TeamsheetDetailPage />} />
                  <Route path="/clubs/:clubId/teamsheets/:teamsheetId/edit" element={<TeamsheetEditPage />} />

                  <Route path="/clubs/:clubId/tactics-boards/:boardId" element={<TacticsBoardEditorPage />} />
                  <Route path="/coaching/playerdata/player" element={<InternalPlayerProfilePage />} />
                  <Route path="/coaching/playerdata/compare" element={<InternalPlayerComparisonPage />} />

                  {/* --- Predictions & Intelligence --- */}
                  <Route path="/predictions" element={<PredictionPage />} />
                  <Route path="/predictions/odds" element={<OddsComparisonPage />} />
                  <Route path="/predictions/hub" element={<PredictionsHub />} />
                  <Route path="/match/lookup" element={<MatchIntelligenceHub />} />
                  <Route path="/season/:leagueCode" element={<SeasonProjectionCentre />} />
                  <Route path="/tactics/:teamSlug" element={<TacticalScoutingDashboard />} />
                  <Route path="/squad/:teamSlug" element={<SquadIntelligenceHub />} />
                  <Route path="/trust" element={<ModelTrustCentre />} />

                  {/* --- Live Football --- */}
                  <Route path="/livefootball" element={<LiveFootballBasePage />} />
                  <Route path="/livefootball/leagues" element={<Leagues />} />
                  <Route path="/livefootball/leagues/compare" element={<LeagueComparePage />} />
                  <Route path="/livefootball/leagues/custom" element={<LeagueCustomPage />} />
                  <Route path="/livefootball/leagues/predict" element={<LeaguePredictPage />} />

                </Route>
              </Route>

              {/* --- Catch-all: 404 --- */}
              <Route path="*" element={<NotFoundPage />} />

            </Routes>
          </RouteErrorBoundary>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
