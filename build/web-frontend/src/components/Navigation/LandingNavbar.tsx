import type { Dispatch, SetStateAction } from "react";
import Popup from "reactjs-popup";
import { LoginButton } from "../Buttons/LoginButton";
import { LoginForm } from "../Forms/LoginForm";
import { SignUpForm } from "../Forms/SignUpForm";
import { TitleLogo } from "../Logo/TitleLogo";
import "./css/LandingNavbar.css";

interface LandingNavbarProps {
  activeForm?: "none" | "login" | "signup";
  setActiveForm?: Dispatch<SetStateAction<"none" | "login" | "signup">>;
}

export const LandingNavbar = ({
  activeForm = "none",
  setActiveForm = () => {},
}: LandingNavbarProps) => {
  return (
    <div className="landingNavbar">
      <div className="titleLogo">
        <TitleLogo />
      </div>
      <div className="loginButtons">
        <LoginButton text="Login" onClick={() => setActiveForm("login")} />
        <LoginButton text="Sign Up" onClick={() => setActiveForm("signup")} colour="#378166a2" />
      </div>

      <Popup
        open={activeForm !== "none"}
        onClose={() => setActiveForm("none")}
        modal
        closeOnDocumentClick={false}
        position="center center"
        overlayStyle={{ pointerEvents: 'none' }}
        contentStyle={{ pointerEvents: 'auto' }}
      >
        <div style={{ position: "relative" }}>
            {activeForm === "login" && (
              <div style={{ position: "relative" }}>
                <button
                  onClick={() => setActiveForm("none")}
                  style={{
                    position: "absolute",
                    top: "10px",
                    right: "10px",
                    zIndex: 10000,
                    background: "white",
                    border: "2px solid #000",
                    borderRadius: "50%",
                    width: "30px",
                    height: "30px",
                    fontSize: "1.2rem",
                    fontWeight: "bold",
                    color: "#000",
                    cursor: "pointer",
                    lineHeight: 1,
                    padding: "0",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    pointerEvents: "auto",
                  }}
                  aria-label="Close"
                >
                  ✕
                </button>
                <LoginForm onSwitchToSignUp={() => setActiveForm("signup")} />
              </div>
            )}
            {activeForm === "signup" && (
              <div style={{ position: "relative" }}>
                <button
                  onClick={() => setActiveForm("none")}
                  style={{
                    position: "absolute",
                    top: "10px",
                    right: "10px",
                    zIndex: 10000,
                    background: "white",
                    border: "2px solid #000",
                    borderRadius: "50%",
                    width: "30px",
                    height: "30px",
                    fontSize: "1.2rem",
                    fontWeight: "bold",
                    color: "#000",
                    cursor: "pointer",
                    lineHeight: 1,
                    padding: "0",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    pointerEvents: "auto",
                  }}
                  aria-label="Close"
                >
                  ✕
                </button>
                <SignUpForm onSwitchToLogin={() => setActiveForm("login")} />
              </div>
            )}
          </div>
      </Popup>
    </div>
  );
};
