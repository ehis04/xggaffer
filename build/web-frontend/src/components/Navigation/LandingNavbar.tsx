import { LoginButton } from "../Buttons/LoginButton";
import { RegisterButton } from "../Buttons/RegisterButton";
import { TitleLogo } from "../Logo/TitleLogo";
import "./css/LandingNavbar.css";

export const LandingNavbar = () => {
  return (
    <div className="landingNavbar">
      <div className="titleLogo">
        <TitleLogo />
      </div>
      <div className="loginButtons">
        <LoginButton />
        <RegisterButton />
      </div>
    </div>
  );
};
