import { useEffect, useState, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { authApi } from '../../services/api/auth';
import { useAuth } from '../../context/useAuth';

export function VerifyEmailCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  const [alreadyVerified, setAlreadyVerified] = useState(false);
  const hasVerified = useRef(false);

  useEffect(() => {
    if (hasVerified.current) return;
    hasVerified.current = true;

    const token = searchParams.get('token');

    if (!token) {
      setStatus('error');
      setError('No verification token provided');
      return;
    }

    const verifyEmail = async () => {
      try {
        const response = await authApi.verifyEmail(token);
        setStatus('success');
        setAlreadyVerified(response.already_verified || false);

        await refreshUser();

        setTimeout(() => {
          navigate('/social', { replace: true });
        }, 2000);
      } catch (err: unknown) {
        setStatus('error');
        setError((err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Verification failed');
      }
    };

    verifyEmail();
  }, [navigate, refreshUser, searchParams]);

  if (status === 'loading') {
    return (
      <div className="verify-callback">
        <div className="verify-callback-card">
          <div className="loading-spinner" />
          <p>Verifying your email...</p>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="verify-callback">
        <div className="verify-callback-card success">
          <h1>{alreadyVerified ? 'Already Verified!' : 'Email Verified!'}</h1>
          <p>
            {alreadyVerified
              ? 'Your email is already verified. Redirecting to social page...'
              : 'Your email has been verified successfully. Redirecting to social page...'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="verify-callback">
      <div className="verify-callback-card error">
        <h1>Verification Failed</h1>
        <p>{error}</p>
        <button onClick={() => navigate('/')} className="btn-primary">
          Go to Home
        </button>
      </div>
    </div>
  );
}

export default VerifyEmailCallbackPage;