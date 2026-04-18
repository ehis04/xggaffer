import { useState } from 'react';
import { HeroSection } from "../../components/Hero/HeroSection";
import { LandingNavbar } from "../../components/Navigation/LandingNavbar";

import './css/LandingPage.css';

const LandingPage = () => {
    const [activeForm, setActiveForm] = useState<"none" | "login" | "signup">("none");

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
