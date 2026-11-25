// --- Framework & Core ---
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, type ComponentType } from "react";
import "./App.css";

// --- Query Client ---
import { queryClient } from "./common/query/queryClient";

// --- Route Guards & Layout ---
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { PublicOnlyRoute } from "./components/auth/PublicOnlyRoute";
import { RouteErrorBoundary } from "./pages/status/RouteErrorBoundary";
import AuthenticatedLayout from "./utils/AuthenticatedLayout";

const namedPage = <T extends Record<string, unknown>, K extends keyof T>(
  loader: () => Promise<T>,
  exportName: K,
) => lazy(async () => ({ default: (await loader())[exportName] as ComponentType }));

const LandingPage = lazy(() => import("./pages/setup/LandingPage"));
const ProfileCreationPage = lazy(() => import("./pages/setup/ProfileCreationPage"));
const RoleAssignPage = namedPage(() => import("./pages/setup/RoleAssignPage"), "RoleAssignPage");
const RoleProfilePage = namedPage(() => import("./pages/setup/RoleProfilePage"), "RoleProfilePage");
const VerifyEmailPromptPage = namedPage(() => import("./pages/setup/VerifyEmailPromptPage"), "VerifyEmailPromptPage");
const VerifyEmailCallbackPage = namedPage(() => import("./pages/setup/VerifyEmailCallbackPage"), "VerifyEmailCallbackPage");
const ForgotPasswordPage = namedPage(() => import("./pages/setup/ForgotPasswordPage"), "ForgotPasswordPage");
const ResetPasswordPage = namedPage(() => import("./pages/setup/ResetPasswordPage"), "ResetPasswordPage");
const UserProfilePage = namedPage(() => import("./pages/user/UserProfilePage"), "UserProfilePage");
const HomePage = lazy(() => import("./pages/home/HomePage"));
const SocialPage = namedPage(() => import("./pages/social/SocialPage"), "SocialPage");
const PostDetailPage = namedPage(() => import("./pages/social/PostDetailPage"), "PostDetailPage");
const TrashPage = lazy(() => import("./pages/social/TrashPage"));
const ArticlesPage = lazy(() => import("./pages/articles/ArticlesPage"));
const FavouriteArticlesPage = lazy(() => import("./pages/articles/FavouriteArticlesPage"));
const ArticleDetailPage = lazy(() => import("./pages/articles/ArticleDetailPage"));
const ArticleProfilePage = lazy(() => import("./pages/articles/ArticleProfilePage"));
const RefereeHome = namedPage(() => import("./pages/referee/RefereeHome"), "RefereeHome");
const CoursePage = namedPage(() => import("./pages/referee/CoursePage"), "CoursePage");
const CoachingBase = namedPage(() => import("./pages/coaching/CoachingBase"), "CoachingBase");
const MyClubsPage = lazy(() => import("./pages/coaching/clubs/MyClubsPage"));
const BrowseClubsPage = lazy(() => import("./pages/coaching/clubs/BrowseClubPage"));
const CreateClubPage = lazy(() => import("./pages/coaching/clubs/CreateClubPage"));
const IndividualClubBase = namedPage(() => import("./pages/coaching/clubs/IndividualClubBase"), "IndividualClubBase");
const ClubDetailsPage = namedPage(() => import("./pages/coaching/clubs/ClubDetails"), "ClubDetailsPage");
const TeamsheetCreatePage = lazy(() => import("./pages/coaching/teamsheets/TeamsheetCreatePage"));
const TeamsheetDetailPage = lazy(() => import("./pages/coaching/teamsheets/TeamsheetDetailPage"));
const TeamsheetEditPage = lazy(() => import("./pages/coaching/teamsheets/TeamsheetEditPage"));
const TeamsheetListPage = lazy(() => import("./pages/coaching/teamsheets/TeamsheetListPage"));
const TacticsBoardEditorPage = lazy(() => import("./pages/coaching/tactics/TacticsBoardEditorPage"));
const InternalPlayerProfilePage = lazy(() => import("./pages/coaching/playerdata/InternalPlayerProfilePage"));
const InternalPlayerComparisonPage = lazy(() => import("./pages/coaching/playerdata/InternalPlayerComparisonPage"));
const PredictionPage = lazy(() => import("./pages/predictions/PredictionPage"));
const OddsComparisonPage = lazy(() => import("./pages/predictions/OddsComparisonPage"));
const PredictionsHub = lazy(() => import("./pages/predictions/PredictionsHub"));
const SeasonProjectionCentre = lazy(() => import("./pages/predictions/SeasonProjectionCentre"));
const MatchIntelligenceHub = lazy(() => import("./pages/predictions/MatchIntelligenceHub"));
const TacticalScoutingDashboard = lazy(() => import("./pages/predictions/TacticalScoutingDashboard"));
const SquadIntelligenceHub = lazy(() => import("./pages/predictions/SquadIntelligenceHub"));
const ModelTrustCentre = lazy(() => import("./pages/predictions/ModelTrustCentre"));
const LiveFootballBasePage = lazy(() => import("./pages/livefootball/LiveFootballBasePage"));
const LiveFootballPage = lazy(() => import("./pages/livefootball/LiveFootballPage"));
const LiveFootballClubsPage = namedPage(() => import("./pages/livefootball/LiveFootballDirectoryPages"), "LiveFootballClubsPage");
const LiveFootballMatchesPage = namedPage(() => import("./pages/livefootball/LiveFootballDirectoryPages"), "LiveFootballMatchesPage");
const LiveFootballPlayersPage = namedPage(() => import("./pages/livefootball/LiveFootballDirectoryPages"), "LiveFootballPlayersPage");
const Leagues = lazy(() => import("./pages/livefootball/leagues/LeaguesPage"));
const LeagueComparePage = lazy(() => import("./pages/livefootball/leagues/LeagueComparePage"));
const LeagueCustomPage = lazy(() => import("./pages/livefootball/leagues/LeagueCustomPage"));
const LeaguePredictPage = lazy(() => import("./pages/livefootball/leagues/LeaguePredictPage"));
const NotFoundPage = namedPage(() => import("./pages/status/NotFoundPage"), "NotFoundPage");

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app">
          <RouteErrorBoundary>
            <Suspense fallback={<div role="status" aria-label="Loading page" />}>
            <Routes>

              {/* --- Unprotected Routes: Account Registration & Auth Flow --- */}
              <Route
                path="/"
                element={
                  <PublicOnlyRoute redirectTo="/home" useFrom={false}>
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

                  {/* --- Home --- */}
                  <Route path="/home" element={<HomePage />} />

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
                  <Route path="/clubs/create" element={<CreateClubPage />} />
                  <Route path="/clubs/browse" element={<BrowseClubsPage />} />
                  <Route path="/clubs/:clubId/" element={<IndividualClubBase />} />
                  <Route path="/clubs/:clubId/teamsheets" element={<TeamsheetListPage />} />
                  <Route path="/clubs/:clubId/teamsheets/new" element={<TeamsheetCreatePage />} />
                  <Route path="/clubs/:clubId/teamsheets/:teamsheetId" element={<TeamsheetDetailPage />} />
                  <Route path="/clubs/:clubId/teamsheets/:teamsheetId/edit" element={<TeamsheetEditPage />} />
                  <Route path="/clubs/:clubId/details" element={<ClubDetailsPage />} />

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
                  <Route path="/tactics" element={<TacticalScoutingDashboard />} />
                  <Route path="/squad/:teamSlug" element={<SquadIntelligenceHub />} />
                  <Route path="/squad" element={<SquadIntelligenceHub />} />
                  <Route path="/trust" element={<ModelTrustCentre />} />

                  {/* --- Live Football --- */}
                  <Route path="/livefootball" element={<LiveFootballBasePage />} />
                  <Route path="/livefootball/browse" element={<LiveFootballPage />} />
                  <Route path="/livefootball/matches" element={<LiveFootballMatchesPage />} />
                  <Route path="/livefootball/clubs" element={<LiveFootballClubsPage />} />
                  <Route path="/livefootball/players" element={<LiveFootballPlayersPage />} />
                  <Route path="/livefootball/leagues" element={<Leagues />} />
                  <Route path="/livefootball/leagues/compare" element={<LeagueComparePage />} />
                  <Route path="/livefootball/leagues/custom" element={<LeagueCustomPage />} />
                  <Route path="/livefootball/leagues/predict" element={<LeaguePredictPage />} />

                </Route>
              </Route>

              {/* --- Catch-all: 404 --- */}
              <Route path="*" element={<NotFoundPage />} />

            </Routes>
            </Suspense>
          </RouteErrorBoundary>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
