import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';

interface PublicOnlyRouteProps {
  children: React.ReactNode;
  redirectTo?: string;
  useFrom?: boolean;
}

export function PublicOnlyRoute({
  children,
  redirectTo = '/social',
  useFrom = true,
}: PublicOnlyRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
      </div>
    );
  }

  if (isAuthenticated) {
    const fromPath = (location.state as { from?: Location })?.from?.pathname;
    const target = useFrom && fromPath ? fromPath : redirectTo;
    return <Navigate to={target} replace />;
  }

  return <>{children}</>;
}

export default PublicOnlyRoute;
