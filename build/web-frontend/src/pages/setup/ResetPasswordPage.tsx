import { useState, useEffect } from 'react';
import type { FormEvent } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { authApi } from '../../services/api/auth';
import { LandingNavbar } from '../../components/Navigation/LandingNavbar';
import './css/ResetPasswordPage.css';

interface FormData {
  newPassword: string;
  confirmPassword: string;
}

export const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  const [formData, setFormData] = useState<FormData>({
    newPassword: '',
    confirmPassword: '',
  });

  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      setError('Invalid or missing reset token. Please request a new password reset.');
    }
  }, [token]);

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

    if (formData.newPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      setIsLoading(false);
      return;
    }

    if (formData.newPassword !== formData.confirmPassword) {
      setError('Passwords do not match');
      setIsLoading(false);
      return;
    }

    try {
      await authApi.resetPassword(token!, formData.newPassword, formData.confirmPassword);
      setSuccess(true);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to reset password';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToLogin = () => {
    navigate('/');
  };

  if (!token) {
    return (
      <div className="landingPage">
        <div className="landingNav">
          <LandingNavbar />
        </div>
        <div className="resetPasswordContainer">
          <div className="form resetPasswordForm error-container">
            <h2 className="form-title">Invalid Link</h2>
            <p className="form-description">
              {error}
            </p>
            <button
              type="button"
              className="button-submit"
              onClick={() => navigate('/forgot-password')}
            >
              Request New Reset Link
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={handleBackToLogin}
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="resetPasswordPage">
      <div className="resetPasswordNav">
        <LandingNavbar />
      </div>
      <div className="resetPasswordContainer">
        {!success ? (
          <form className="form resetPasswordForm" onSubmit={handleSubmit}>
            <h2 className="form-title">Create New Password</h2>
            
            <p className="form-description">
              Please enter your new password below.
            </p>

            {error && <div className="error-message">{error}</div>}

            <div className="flex-column">
              <label htmlFor="newPassword">New Password</label>
            </div>
            <div className="inputForm">
              <input
                id="newPassword"
                type="password"
                className="input"
                placeholder="Enter new password"
                value={formData.newPassword}
                onChange={handleInputChange}
                required
              />
            </div>

            <div className="flex-column">
              <label htmlFor="confirmPassword">Confirm Password</label>
            </div>
            <div className="inputForm">
              <input
                id="confirmPassword"
                type="password"
                className="input"
                placeholder="Confirm password"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                required
              />
            </div>

            <p className="password-hint">
              Password must be at least 8 characters long
            </p>

            <button className="button-submit" type="submit" disabled={isLoading}>
              {isLoading ? 'Resetting...' : 'Reset Password'}
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
          <div className="form resetPasswordForm success-container">
            <h2 className="form-title">Password Reset Successful</h2>
            <p className="form-description">
              Your password has been successfully reset.
            </p>
            <p className="form-description">
              You can now login with your new password.
            </p>
            <button
              type="button"
              className="button-submit"
              onClick={handleBackToLogin}
            >
              Go to Login
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResetPasswordPage;
