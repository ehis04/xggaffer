import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './App.css'



import TeamsheetListPage from './components/pages/coaching/teamsheets/TeamsheetListPage';
import TeamsheetDetailPage from './components/pages/coaching/teamsheets/TeamsheetDetailPage';



//Pages
import QuizBase from './components/pages/reffing/quiz/QuizBase';
import ControlBase from './components/pages/reffing/controlTraining/ControlBase';
import ArticleBase from './components/pages/reffing/article/ArticleBase';
import FitnessBase from './components/pages/reffing/fitness/FitnessBase';
import SituationBase from './components/pages/reffing/situation/SituationBase';
import ChangesTimeline from './components/pages/reffing/quiz/ChangesTimeLine';
import LawDetail from './components/pages/reffing/quiz/LawDetails';

import LawsList from './components/pages/reffing/quiz/LawsList';

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
import TeamsheetDetail from './components/pages/coaching/teamsheets/TeamsheetDetail';
import TeamsheetCreatePage from './components/pages/coaching/teamsheets/TeamsheetCreatePage'
import TeamsheetList from './components/pages/coaching/teamsheets/TeamsheetList';

import LandingPage from './components/pages/setup/LandingPage';
import RefBase from './components/pages/reffing/RefBase';
import { SocialPage } from './components/pages/social/SocialPage';

function App() {

  return (
    <BrowserRouter>
    <div className='app'>
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
        <Route path="/clubs/:clubId/teamsheets" element={<TeamsheetListPage />} />
        <Route path="/clubs/:clubId/teamsheets/new" element={<TeamsheetCreatePage />} />
        <Route path="/clubs/:clubId/teamsheets/:teamsheetId" element={<TeamsheetDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
    </BrowserRouter>
  )
}

export default App
