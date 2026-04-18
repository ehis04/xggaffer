import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../../services/api/auth';
import { LandingNavbar } from '../../components/Navigation/LandingNavbar';
import './css/ForgotPasswordPage.css';

export const ForgotPasswordPage = () => {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await authApi.requestPasswordReset(email);
      setSubmitted(true);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to process password reset request';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToLogin = () => {
    navigate('/');
  };

  return (
    <div className="forgotPasswordPage">
      <div className="forgotPasswordNav">
        <LandingNavbar />
      </div>
      <div className="forgotPasswordContainer">
        {!submitted ? (
          <form className="form forgotPasswordForm" onSubmit={handleSubmit}>
            <h2 className="form-title">Reset Password</h2>
            
            <p className="form-description">
              Enter your email address and we'll send you a link to reset your password.
            </p>

            {error && <div className="error-message">{error}</div>}

            <div className="flex-column">
              <label htmlFor="email">Email</label>
            </div>
            <div className="inputForm">
              <input
                id="email"
                type="email"
                className="input"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <button className="button-submit" type="submit" disabled={isLoading}>
              {isLoading ? 'Sending...' : 'Send Reset Link'}
            </button>

            <button
              type="button"
              className="button-secondary"
              onClick={handleBackToLogin}
            >
              Back to Login
            </button>
          </form>
        ) : (
          <div className="form forgotPasswordForm success-container">
            <h2 className="form-title">Check Your Email</h2>
            <p className="form-description">
              We've sent a password reset link to <strong>{email}</strong>
            </p>
            <p className="form-description">
              Please check your email and click the link to reset your password.
            </p>
            <p className="form-description small">
              The link will expire in 1 hour.
            </p>
            <button
              type="button"
              className="button-submit"
              onClick={handleBackToLogin}
            >
              Back to Login
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
