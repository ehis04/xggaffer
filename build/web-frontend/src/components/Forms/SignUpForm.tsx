import "./css/LoginForm.css";
import googleIcon from "../../images/logos/google-svg.svg";

export const SignUpForm = () => {
  return (
    <form className="form">
      <div className="flex-column">
        <label htmlFor="email"> Email </label>
      </div>
      <div className="inputForm">
        <input
          id="email"
          type="text"
          className="input"
          placeholder="Enter your Email"
        />
      </div>
      <div className="flex-column">
        <label htmlFor="email"> First Name </label>
      </div>
      <div className="inputForm">
        <input
          id="fname"
          type="text"
          className="input"
          placeholder="Enter your First Name"
        />
      </div>
      <div className="flex-column">
        <label htmlFor="email"> Last Name </label>
      </div>
      <div className="inputForm">
        <input
          id="lname"
          type="text"
          className="input"
          placeholder="Enter your Last Name"
        />
      </div>
      <div className="flex-column">
        <label htmlFor="password"> Password </label>
      </div>
      <div className="inputForm">
        <input
          id="password"
          type="password"
          className="input"
          placeholder="Enter your Password"
        />
      </div>
      <div className="flex-row">
        <div>
          <input id="rememberMe" type="checkbox" />
          <label htmlFor="rememberMe"> Remember me </label>
        </div>
        <span className="span"> Forgot your password? </span>
      </div>
      <button className="button-submit">Sign Up</button>
      <p className="p">
        Don't have an account? <span className="span"> Login </span>
      </p>
      <p className="p line"> Or With </p>
      <div className="google-flex-row">
        <button className="btn-google">
          <img
            src={googleIcon}
            alt="Google logo"
            width={24}
            height={30}
        />
        </button>
      </div>
    </form>
  );
};
