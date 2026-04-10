import './css/LoginForm.css';
import googleIcon from '../../images/logos/google-svg.svg';
import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';
import type { FormEvent } from 'react';

interface LoginFormData {
  email: string;
  password: string;
  rememberMe: boolean;
}

export const LoginForm = () => {
  const [formData, setFormData] = useState<LoginFormData>({
    email: '',
    password: '',
    rememberMe: false,
  });
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: Location })?.from?.pathname || '/social';

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [id]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login({
        email: formData.email,
        password: formData.password,
        remember_me: formData.rememberMe,
      });


      navigate(from, { replace: true });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred during login';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form className="form" onSubmit={handleSubmit}>
      {error && <div className="error-message">{error}</div>}

      <div className="flex-column">
        <label htmlFor="email">Email</label>
      </div>
      <div className="inputForm">
        <input
          id="email"
          type="email"
          className="input"
          placeholder="Enter your Email"
          value={formData.email}
          onChange={handleInputChange}
          required
        />
      </div>

      <div className="flex-column">
        <label htmlFor="password">Password</label>
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
          <label htmlFor="rememberMe">Remember me</label>
        </div>
        <span className="span">Forgot your password?</span>
      </div>

      <button className="button-submit" type="submit" disabled={isLoading}>
        {isLoading ? 'Signing In...' : 'Sign In'}
      </button>

      <p className="p">
        Don't have an account? <span className="span">Sign Up</span>
      </p>
      <p className="p line">Or With</p>
      <div className="google-flex-row">
        <button type="button" className="btn-google">
          <img src={googleIcon} alt="Google logo" width={24} height={30} />
        </button>
      </div>
    </form>
  );
};