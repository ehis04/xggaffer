import './css/LoginForm.css';
import googleIcon from '../../images/logos/google-svg.svg';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';
import type { FormEvent } from 'react';

interface RegisterFormData {
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  password: string;
}

interface SignUpFormProps {
  onSwitchToLogin?: () => void;
}

export const SignUpForm = ({ onSwitchToLogin }: SignUpFormProps = {}) => {
  const [formData, setFormData] = useState<RegisterFormData>({
    email: '',
    username: '',
    first_name: '',
    last_name: '',
    password: '',
  });
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [id]: value,
    }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await register({
        email: formData.email,
        username: formData.username || undefined,
        first_name: formData.first_name,
        last_name: formData.last_name,
        password: formData.password,
      });

      // New users should always start the setup flow at profile creation.
      navigate('/create/profile', { replace: true });
    } catch (err) {
      const apiError = err as Error & { data?: Record<string, string[]> };
      if (apiError.data && typeof apiError.data === 'object') {
        const messages = Object.values(apiError.data).flat().join(' ');
        setError(messages || apiError.message);
      } else {
        setError(apiError.message || 'An error occurred during registration');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form id="register-form" className="form" onSubmit={handleSubmit}>
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
        <label htmlFor="username">Username</label>
      </div>
      <div className="inputForm">
        <input
          id="username"
          type="text"
          className="input"
          placeholder="Enter your Username"
          value={formData.username}
          onChange={handleInputChange}
        />
      </div>

      <div className="flex-column">
        <label htmlFor="first_name">First Name</label>
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
        <label htmlFor="last_name">Last Name</label>
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
          minLength={8}
          required
        />
      </div>

      <button className="button-submit" type="submit" disabled={isLoading}>
        {isLoading ? 'Creating Account...' : 'Sign Up'}
      </button>

      <p className="p">
        Already have an account?{' '}
        <span className="span" onClick={onSwitchToLogin}>
          Login
        </span>
      </p>
    </form>
  );
};