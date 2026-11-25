import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { HeroSection } from "../../components/Hero/HeroSection";
import { LandingNavbar } from "../../components/Navigation/LandingNavbar";

import './css/LandingPage.css';

const LandingPage = () => {
    const { state } = useLocation();
    const [activeForm, setActiveForm] = useState<"none" | "login" | "signup">(
        state?.showLogin ? "login" : "none",
    );

    return (
        <div className="landingPage">
            <div className="landingNav">
                <LandingNavbar activeForm={activeForm} setActiveForm={setActiveForm} />
            </div>
            <div className="landingHero">
                <HeroSection onGetStarted={() => setActiveForm("signup")} />
            </div>
        </div>
    );
};

export default LandingPage;
