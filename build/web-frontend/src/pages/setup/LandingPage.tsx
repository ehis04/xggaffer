import { HeroSection } from "../../components/Hero/HeroSection";
import { LandingNavbar } from "../../components/Navigation/LandingNavbar";

import './css/LandingPage.css';

const LandingPage = () => {
    return (
        <div className="landingPage">
            <div className="landingNav">
                <LandingNavbar/>
            </div>
            <div className="landingHero">
                <HeroSection/>
            </div>
        </div>
    )
}

export default LandingPage;