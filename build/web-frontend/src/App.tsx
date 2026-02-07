import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { PublicOnlyRoute } from './components/auth/PublicOnlyRoute';

// Setup pages
import LandingPage from './pages/setup/LandingPage';
import ProfileCreationPage from './pages/setup/ProfileCreationPage';
import { RoleAssignPage } from './pages/setup/RoleAssignPage';
import { RoleProfilePage } from './pages/setup/RoleProfilePage';
import { VerifyEmailPromptPage } from './pages/setup/VerifyEmailPromptPage';
import { VerifyEmailCallbackPage } from './pages/setup/VerifyEmailCallbackPage';

// Social pages
import { SocialPage } from './pages/social/SocialPage';
import { PostDetailPage } from './pages/social/PostDetailPage';

// Reffing pages
import RefBase from './pages/reffing/RefBase';
import QuizBase from './pages/reffing/quiz/QuizBase';
import ControlBase from './pages/reffing/controlTraining/ControlBase';
import ArticleBase from './pages/reffing/article/ArticleBase';
import FitnessBase from './pages/reffing/fitness/FitnessBase';
import SituationBase from './pages/reffing/situation/SituationBase';
import ChangesTimeline from './pages/reffing/quiz/ChangesTimeLine';
import LawDetail from './pages/reffing/quiz/LawDetails';
import LawsList from './pages/reffing/quiz/LawsList';

// Coaching pages
import { CoachingBase } from './pages/coaching/CoachingBase';
import TeamsheetDetail from './pages/coaching/teamsheets/TeamsheetDetail';
import TeamsheetList from './pages/coaching/teamsheets/TeamsheetList';
import TeamsheetListPage from './pages/coaching/teamsheets/TeamsheetListPage';
import TeamsheetCreatePage from './pages/coaching/teamsheets/TeamsheetCreatePage';
import TeamsheetDetailPage from './pages/coaching/teamsheets/TeamsheetDetailPage';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          {/* Public only route */}
          <Route path="/" element={
            <PublicOnlyRoute redirectTo="/social" useFrom={false}>
              <LandingPage />
            </PublicOnlyRoute>
          } />

          {/* Unprotected route (verification callback) */}
          <Route path="/verify-email/confirm" element={<VerifyEmailCallbackPage />} />

          {/* Protected routes - verification NOT required */}
          <Route element={<ProtectedRoute requireVerified={false} />}>
            <Route path="/verify-email" element={<VerifyEmailPromptPage />} />
            <Route path="/create/profile" element={<ProfileCreationPage />} />
            <Route path="/create/profile/role" element={<RoleAssignPage />} />
            <Route path="/create/profile/role/details" element={<RoleProfilePage />} />
          </Route>

          {/* Protected routes - verification required */}
          <Route element={<ProtectedRoute />}>
            {/* Social */}
            <Route path="/social" element={<SocialPage />} />
            <Route path="/social/post/:postId" element={<PostDetailPage />} />

            {/* Reffing */}
            <Route path="/refbase" element={<RefBase />} />
            <Route path="/quizbase" element={<QuizBase />} />
            <Route path="/controlBase" element={<ControlBase />} />
            <Route path="/articleBase" element={<ArticleBase />} />
            <Route path="/fitnessBase" element={<FitnessBase />} />
            <Route path="/situationBase" element={<SituationBase />} />
            <Route path="/laws" element={<LawsList />} />
            <Route path="/laws/:lawNumber" element={<LawDetail />} />
            <Route path="/laws/changes" element={<ChangesTimeline />} />

            {/* Coaching */}
            <Route path="/coaching" element={<CoachingBase />} />
            <Route path="/coaching/teamsheets" element={<TeamsheetList />} />
            <Route path="/coaching/teamsheets/:id" element={<TeamsheetDetail />} />
            <Route path="/clubs/:clubId/teamsheets" element={<TeamsheetListPage />} />
            <Route path="/clubs/:clubId/teamsheets/new" element={<TeamsheetCreatePage />} />
            <Route path="/clubs/:clubId/teamsheets/:teamsheetId" element={<TeamsheetDetailPage />} />
          </Route>

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
