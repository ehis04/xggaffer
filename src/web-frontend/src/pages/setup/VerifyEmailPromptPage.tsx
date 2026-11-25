import { useState } from 'react';
import { useAuth } from '../../context/useAuth';
import { useLocation, useNavigate } from 'react-router-dom';
import styles from './css/VerifyEmail.module.css';

export function VerifyEmailPromptPage() {
  const { user, resendVerificationEmail, refreshUser, logout } = useAuth();
  const navigate = useNavigate();
  const { state } = useLocation();
  const [sending, setSending] = useState(false);
  const [checking, setChecking] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(
    state?.verificationEmailSent === false
      ? 'We couldn’t send the verification email. Use Resend Email to try again.'
      : null,
  );

  const handleResend = async () => {
    setSending(true);
    setError(null);
    try {
      await resendVerificationEmail();
      setSent(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to send verification email');
    } finally {
      setSending(false);
    }
  };

  const handleCheckStatus = async () => {
    setChecking(true);
    setError(null);
    try {
      const currentUser = await refreshUser();
      if (currentUser && currentUser.id !== user?.id) {
        setError('The active account changed. Sign in to the account you want to verify.');
      } else if (currentUser?.email_verified) {
        navigate(state?.newSignup ? '/create/profile' : '/home', { replace: true });
      } else {
        setError('Your email is not verified yet. Click the link in your inbox, then try again.');
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not check verification status');
    } finally {
      setChecking(false);
    }
  };

  const handleSignOut = async () => {
    setSigningOut(true);
    try {
      await logout();
      navigate('/', { replace: true, state: { showLogin: true } });
    } catch {
      setError('Could not sign out. Please try again.');
      setSigningOut(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1>Verify Your Email</h1>
        <p>
          Look for a verification email at <strong>{user?.email}</strong> and click the link.
        </p>

        {sent && (
          <p role="status">
            Verification email sent! Check your inbox.
          </p>
        )}

        {error && (
          <p role="alert">{error}</p>
        )}

        <div className={styles.actions}>
          <button
            onClick={handleResend}
            disabled={sending || signingOut}
            className={styles.secondary}
          >
            {sending ? 'Sending...' : 'Resend Email'}
          </button>

          <button
            onClick={handleCheckStatus}
            disabled={checking || signingOut}
            className={styles.primary}
          >
            {checking ? 'Checking…' : 'Check verification'}
          </button>
          <button onClick={handleSignOut} disabled={signingOut || sending || checking} className={styles.secondary}>
            {signingOut ? 'Signing out…' : 'Sign out'}
          </button>
        </div>

        <p>
          Didn't receive the email? Check your spam folder or click resend.
        </p>
      </div>
    </div>
  );
}

export default VerifyEmailPromptPage;
