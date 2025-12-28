import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './App.css'

//Pages
import LandingPage from './pages/setup/LandingPage'
import RefBase from './pages/reffing/RefBase'
import { SocialPage } from './pages/social/SocialPage';

function App() {

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/refbase" element={<RefBase />} />
        <Route path="/social" element={< SocialPage/>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App