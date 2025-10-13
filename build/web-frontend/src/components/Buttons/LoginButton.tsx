import { LoginForm } from "../Forms/LoginForm";
import "./css/LoginButton.css";
import Popup from "reactjs-popup";

export const LoginButton = () => {
  return (
    <Popup
      position="center center"
      modal
      trigger={
        <button className="loginButton">
          <div className="body">
            <p> Login</p>
          </div>
        </button>
      }
    >
      <div>
        <LoginForm/>
      </div>
    </Popup>
  );
};
