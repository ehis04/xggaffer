import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'



//Pages
import LandingPage from './components/pages/setup/LandingPage';
import RefBase from './components/pages/reffing/RefBase';
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
import TeamsheetList from './components/pages/coaching/teamsheets/TeamsheetList';

function App() {
  const [count, setCount] = useState(0)

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
      </Routes>
    </BrowserRouter>
  )
}

export default App