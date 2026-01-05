// src/App.tsx

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

// Auth components
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { PublicOnlyRoute } from './components/auth/PublicOnlyRoute';

// Pages
import QuizBase from './pages/reffing/quiz/QuizBase';
import ControlBase from './pages/reffing/controlTraining/ControlBase';
import ArticleBase from './pages/reffing/article/ArticleBase';
import FitnessBase from './pages/reffing/fitness/FitnessBase';
import SituationBase from './pages/reffing/situation/SituationBase';
import ChangesTimeline from './pages/reffing/quiz/ChangesTimeLine';
import LawDetail from './pages/reffing/quiz/LawDetails';
import LawsList from './pages/reffing/quiz/LawsList';
import TeamsheetDetail from './pages/coaching/teamsheets/TeamsheetDetail';
import TeamsheetList from './pages/coaching/teamsheets/TeamsheetList';
import LandingPage from './pages/setup/LandingPage';
import RefBase from './pages/reffing/RefBase';
import { SocialPage } from './pages/social/SocialPage';
import { PostDetailPage } from './pages/social/PostDetailPage';
import ProfileCreationPage from './pages/setup/ProfileCreationPage';
import { RoleAssignPage } from './pages/setup/RoleAssignPage';
import { RoleProfilePage } from './pages/setup/RoleProfilePage';
import TeamsheetListPage from './pages/coaching/teamsheets/TeamsheetListPage';
import TeamsheetCreatePage from './pages/coaching/teamsheets/TeamsheetCreatePage';
import TeamsheetDetailPage from './pages/coaching/teamsheets/TeamsheetDetailPage';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          <Route
            path="/"
            element={
              <PublicOnlyRoute redirectTo="/create/profile" useFrom={false}>
                <LandingPage />
              </PublicOnlyRoute>
            }
          />


          <Route
            path="/social"
            element={
              <ProtectedRoute>
                <SocialPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/social/post/:postId"
            element={
              <ProtectedRoute>
                <PostDetailPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/create/profile"
            element={
              <ProtectedRoute>
                <ProfileCreationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/create/profile/role"
            element={
              <ProtectedRoute>
                <RoleAssignPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/create/profile/role/details"
            element={
              <ProtectedRoute>
                <RoleProfilePage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/refbase"
            element={
              <ProtectedRoute>
                <RefBase />
              </ProtectedRoute>
            }
          />
          <Route
            path="/quizbase"
            element={
              <ProtectedRoute>
                <QuizBase />
              </ProtectedRoute>
            }
          />
          <Route
            path="/controlBase"
            element={
              <ProtectedRoute>
                <ControlBase />
              </ProtectedRoute>
            }
          />
          <Route
            path="/articleBase"
            element={
              <ProtectedRoute>
                <ArticleBase />
              </ProtectedRoute>
            }
          />
          <Route
            path="/fitnessBase"
            element={
              <ProtectedRoute>
                <FitnessBase />
              </ProtectedRoute>
            }
          />
          <Route
            path="/situationBase"
            element={
              <ProtectedRoute>
                <SituationBase />
              </ProtectedRoute>
            }
          />

          <Route 
            path="/laws" 
            element={
              <ProtectedRoute>
                <LawsList />
              </ProtectedRoute>
            }
          />
          <Route 
            path="/laws/:lawNumber" 
            element={
            <ProtectedRoute>
              <LawDetail />
            </ProtectedRoute>
            } 
          />
          <Route 
            path="/laws/changes" 
            element={
              <ProtectedRoute>
                <ChangesTimeline />
              </ProtectedRoute>
            }
          />

          <Route
            path="/coaching/teamsheets"
            element={
              <ProtectedRoute>
                <TeamsheetList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/coaching/teamsheets/:id"
            element={
              <ProtectedRoute>
                <TeamsheetDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clubs/:clubId/teamsheets"
            element={
              <ProtectedRoute>
                <TeamsheetListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clubs/:clubId/teamsheets/new"
            element={
              <ProtectedRoute>
                <TeamsheetCreatePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clubs/:clubId/teamsheets/:teamsheetId"
            element={
              <ProtectedRoute>
                <TeamsheetDetailPage />
              </ProtectedRoute>
            }
          />

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
