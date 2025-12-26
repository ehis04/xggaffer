import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState } from 'react'
import './App.css'

//Pages
import LandingPage from './pages/setup/LandingPage'
import RefBase from './pages/reffing/RefBase'
import { Predictions } from './pages/Predictions/predictions';

function App() {
  const [count, setCount] = useState(0)

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/predictions" element={<Predictions />} />
        <Route path="/refbase" element={<RefBase />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App