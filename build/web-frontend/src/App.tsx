import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './App.css'



//Pages
import QuizBase from './pages/reffing/quiz/QuizBase';
import ControlBase from './pages/reffing/controlTraining/ControlBase';
import ArticleBase from './pages/reffing/article/ArticleBase';
import FitnessBase from './pages/reffing/fitness/FitnessBase';
import SituationBase from './pages/reffing/situation/SituationBase';
import ChangesTimeline from './pages/reffing/quiz/ChangesTimeLine';
import LawDetail from './pages/reffing/quiz/LawDetails';
import LawsList from './pages/reffing/quiz/LawsList';

// Coaching - teamsheets
// Temporary local TeamsheetCreate component to satisfy the import until the real file exists
const TeamsheetCreate = () => {
  return (
    <div>
      <h1>Create Teamsheet</h1>
      <p>Placeholder component — implement your form here.</p>
    </div>
  );
};
import TeamsheetDetail from './pages/coaching/teamsheets/TeamsheetDetail';
import TeamsheetList from './pages/coaching/teamsheets/TeamsheetList';
import LandingPage from './pages/setup/LandingPage'
import RefBase from './pages/reffing/RefBase'
import { SocialPage } from './pages/social/SocialPage';
import { PostDetailPage } from './pages/social/PostDetailPage';
import ProfileCreationPage from './pages/setup/ProfileCreationPage';
import { RoleAssignForm } from './components/Forms/RoleAssignForm';
import { RoleProfilePage } from './pages/setup/RoleProfilePage';
import { UserProfilePage } from './pages/user/UserProfilePage';
import { RefereeHome } from './pages/referee/RefereeHome';
import { QuizPage } from './pages/referee/QuizPage';

function App() {

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/refbase" element={<RefBase />} />
        <Route path="/quizbase" element={<QuizBase />} />
        <Route path="/controlBase" element={<ControlBase />} /> 
        <Route path="/articleBase" element={<ArticleBase />} />
        <Route path="/fitnessBase" element={<FitnessBase />} />
        <Route path="/situationBase" element={<SituationBase />} />
        <Route path="/laws" element={<LawsList />} />
        <Route path="/laws/:lawNumber" element={<LawDetail />} />
        <Route path="/laws/changes" element={<ChangesTimeline />} />
        <Route path="/coaching/teamsheets" element={<TeamsheetList />} />
        <Route path='/coaching/teamsheets/create' element={<TeamsheetCreate />} />
        <Route path='/coaching/teamsheets/:id' element={<TeamsheetDetail />} />
        <Route path="/social" element={< SocialPage/>} />
        <Route path='/social/post/:postId' element={<PostDetailPage />} />
        <Route path="/create/profile" element={<ProfileCreationPage />} />
        <Route path="/create/profile/role" element={<RoleAssignForm />} />
        <Route path="/create/profile/role/details" element={<RoleProfilePage />} />
        <Route path="/profile/:username" element={<UserProfilePage />} />
        <Route path="/referee/" element={<RefereeHome />} />
        <Route path="/referee/quiz/:quizId" element={<QuizPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App