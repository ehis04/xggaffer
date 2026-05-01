import { useState } from 'react';
import { useAuth } from '../../context/useAuth';
import { useNavigate } from 'react-router-dom';
import authApi from '../../services/api/auth';

export function VerifyEmailPromptPage() {
  const { user, resendVerificationEmail, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleResend = async () => {
    setSending(true);
    setError(null);
    try {
      await resendVerificationEmail();
      setSent(true);
    } catch (err: unknown) {
      setError((err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Failed to send verification email');
    } finally {
      setSending(false);
    }
  };

  const handleCheckStatus = async () => {
    setError(null);
    try {
      const status = await authApi.getVerificationStatus();
      await refreshUser();
      if (status.email_verified) {
        navigate('/social', { replace: true });
      } else {
        setError('Your email is not verified yet. Click the link in your inbox, then try again.');
      }
    } catch (err: unknown) {
      setError((err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Could not check verification status');
    }
  };

  return (
    <div className="verify-email-prompt">
      <div className="verify-email-card">
        <h1>Verify Your Email</h1>
        <p>
          We've sent a verification email to <strong>{user?.email}</strong>.
          Please check your inbox and click the verification link.
        </p>

        {sent && (
          <div className="success-message">
            Verification email sent! Check your inbox.
          </div>
        )}

        {error && (
          <div className="error-message">{error}</div>
        )}

        <div className="verify-email-actions">
          <button
            onClick={handleResend}
            disabled={sending}
            className="btn-secondary"
          >
            {sending ? 'Sending...' : 'Resend Email'}
          </button>

          <button
            onClick={handleCheckStatus}
            className="btn-primary"
          >
            I've Verified My Email
          </button>
        </div>

        <p className="verify-email-note">
          Didn't receive the email? Check your spam folder or click resend.
        </p>
      </div>
    </div>
  );
}

export default VerifyEmailPromptPage;
