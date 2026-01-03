import { LoginButton } from "../Buttons/LoginButton";
import { LoginForm } from "../Forms/LoginForm";
import { SignUpForm } from "../Forms/SignUpForm";
import { TitleLogo } from "../Logo/TitleLogo";
import "./css/LandingNavbar.css";

export const LandingNavbar = () => {
  return (
    <div className="landingNavbar">
      <div className="titleLogo">
        <TitleLogo />
      </div>
      <div className="loginButtons">
        <LoginButton text="Login" popup={true} popupContent={<LoginForm />} />
        <LoginButton text="Register" popup={true} popupContent={<SignUpForm />} colour="#378166a2" />
      </div>
    </div>
  );
};
