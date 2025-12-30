import "./css/LoginForm.css";
import googleIcon from "../../images/logos/google-svg.svg";
import { Api_Endpoints } from "../../services/api/AuthenticateUserApi";
import type { FormEvent } from "react";
import { useState } from "react";

interface RegisterFormData {
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  password: string;
}

interface RegisterResponse {
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

export const SignUpForm = () => {
  const [formData, setFormData] = useState<RegisterFormData>({
    email: "",
    username: "",
    first_name: "",
    last_name: "",
    password: "",
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
      const response = await fetch(Api_Endpoints.REGISTER, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: formData.email,
          username: formData.username,
          first_name: formData.first_name,
          last_name: formData.last_name,
          password: formData.password,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Registration Failed");
      }

      const data: RegisterResponse = await response.json();

      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);

      localStorage.setItem("user", JSON.stringify(data.user));

      console.log("Registration successful: ", data);
      globalThis.location.href = "http://localhost:5173/create/profile";
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "An error occured during registration"
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
          type="text"
          className="input"
          placeholder="Enter your Email"
          value={formData.email}
          onChange={handleInputChange}
          required
        />
      </div>
      <div className="flex-column">
        <label htmlFor="username"> Username </label>
      </div>
      <div className="inputForm">
        <input
          id='username'
          type="text"
          className="input"
          placeholder="Enter your Username"
          value={formData.username}
          onChange={handleInputChange}
          required
        />
      </div>
      <div className="flex-column">
        <label htmlFor="first_name"> First Name </label>
      </div>
      <div className="inputForm">
        <input
          id="first_name"
          type="text"
          className="input"
          placeholder="Enter your First Name"
          value={formData.first_name}
          onChange={handleInputChange}
          required
        />
      </div>
      <div className="flex-column">
        <label htmlFor="last_name"> Last Name </label>
      </div>
      <div className="inputForm">
        <input
          id="last_name"
          type="text"
          className="input"
          placeholder="Enter your Last Name"
          value={formData.last_name}
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
      <button className="button-submit" type="submit" disabled={isLoading}>
        {isLoading ? "Signing In..." : "Sign In"}
      </button>
      <p className="p">
        Already have an account? <span className="span"> Login </span>
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
