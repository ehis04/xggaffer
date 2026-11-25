import { useEffect, useState, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { authApi } from '../../services/api/auth';
import styles from './css/VerifyEmail.module.css';

export function VerifyEmailCallbackPage() {
  const [searchParams] = useSearchParams();
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

      } catch (err: unknown) {
        setStatus('error');
        setError(err instanceof Error ? err.message : 'Verification failed');
      }
    };

    verifyEmail();
  }, [searchParams]);

  if (status === 'loading') {
    return (
      <div className={styles.page}>
        <div className={styles.card}>
          <p role="status">Verifying your email…</p>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className={styles.page}>
        <div className={styles.card}>
          <h1>{alreadyVerified ? 'Already Verified!' : 'Email Verified!'}</h1>
          <p>Return to your original signup tab and check verification, or sign in to the account you verified.</p>
          <Link to="/" state={{ showLogin: true }} className={styles.primary}>Return to xgGaffer</Link>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1>Verification Failed</h1>
        <p role="alert">{error}</p>
        <Link to="/" state={{ showLogin: true }} className={styles.primary}>Return to sign in</Link>
      </div>
    </div>
  );
}

export default VerifyEmailCallbackPage;
