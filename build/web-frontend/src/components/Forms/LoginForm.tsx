import "./css/LoginForm.css";
import googleIcon from "../../images/logos/google-svg.svg";
import { useState } from "react";
import type { FormEvent } from "react";

interface LoginFormData {
  email: string;
  password: string;
  rememberMe: boolean;
}

interface LoginResponse {
  access: string;
  refresh: string;
  user: {
    id: number;
    email: string;
    username: string;
    first_name: string;
    last_name: string;
  };
}

export const LoginForm = () => {
  const [formData, setFormData] = useState<LoginFormData>({
    email: "",
    password: "",
    rememberMe: false,
  });
  const [error, setError] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [id]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/users/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Login failed");
      }

      const data: LoginResponse = await response.json();

      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);

      localStorage.setItem("user", JSON.stringify(data.user));

      console.log("Login successful: ", data);
      globalThis.location.href = "http://localhost:5173/social";
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "An error occured during login"
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form className="form" onSubmit={handleSubmit}>
      <div className="flex-column">
        <label htmlFor="email"> Email </label>
      </div>
      <div className="inputForm">
        <input
          id="email"
          type="enail"
          className="input"
          placeholder="Enter your Email"
          value={formData.email}
          onChange={handleInputChange}
          required
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
          value={formData.password}
          onChange={handleInputChange}
          required
        />
      </div>
      <div className="flex-row">
        <div>
          <input
            id="rememberMe"
            type="checkbox"
            checked={formData.rememberMe}
            onChange={handleInputChange}
          />
          <label htmlFor="rememberMe"> Remember me </label>
        </div>
        <span className="span"> Forgot your password? </span>
      </div>
      <button className="button-submit" type="submit" disabled={isLoading}>
        {isLoading ? "Signing In..." : "Sign In"}
      </button>
      <p className="p">
        Don't have an account? <span className="span"> Sign Up </span>
      </p>
      <p className="p line"> Or With </p>
      <div className="google-flex-row">
        <button className="btn-google">
          <img src={googleIcon} alt="Google logo" width={24} height={30} />
        </button>
      </div>
    </form>
  );
};
