import { Navigate, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEffect, useState } from 'react';
import { usersApi } from '../../services/api/usersApi';

interface ProtectedRouteProps {
  children?: React.ReactNode;
  requireVerified?: boolean;
}

export function ProtectedRoute({ children, requireVerified = true }: ProtectedRouteProps) {
  const { isAuthenticated, isEmailVerified, isLoading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [checkingProfile, setCheckingProfile] = useState(true);

  useEffect(() => {
    let mounted = true;

    const verifyProfile = async () => {
      if (!isAuthenticated) {
        if (mounted) setCheckingProfile(false);
        return;
      }

      if (location.pathname.startsWith('/create/profile')) {
        if (mounted) setCheckingProfile(false);
        return;
      }

      if (location.pathname === '/verify-email') {
        if (mounted) setCheckingProfile(false);
        return;
      }

      try {
        const profile = await usersApi.getMyProfile();
        if (!profile.roles || profile.roles.length === 0) {
          navigate('/create/profile/role', { replace: true });
        }
      } catch (err: any) {
        const status = err?.response?.status ?? err?.status;
        if (status === 404) {
          navigate('/create/profile', { replace: true });
        } else {
          console.error('Error verifying user profile:', err);
        }
      } finally {
        if (mounted) setCheckingProfile(false);
      }
    };

    verifyProfile();

    return () => {
      mounted = false;
    };
  }, [isAuthenticated, location.pathname, navigate]);

  if (isLoading || checkingProfile) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  if (requireVerified && !isEmailVerified && !location.pathname.startsWith('/create/profile')) {
    return <Navigate to="/verify-email" replace />;
  }

  return children ? <>{children}</> : <Outlet />;
}

export default ProtectedRoute;