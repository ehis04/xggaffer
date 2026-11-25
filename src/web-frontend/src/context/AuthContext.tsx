import {
  createContext,
  Fragment,
  useState,
  useRef,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import { authApi, type User, type LoginCredentials, type RegisterData } from '../services/api/auth';
import { changeApiSession } from '../services/api/client';
import { queryClient } from '../common/query/queryClient';
import { resetUserProfileCache } from '../components/Navigation/functions/getUserProfile';

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isEmailVerified: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<boolean | undefined>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
  sendVerificationEmail: () => Promise<void>;
  resendVerificationEmail: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const SESSION_CHANGED_KEY = 'xggaffer:session-changed';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const session = useRef(0);
  const currentUserRequest = useRef(0);
  const activeUserId = useRef<number | null>(null);

  const applyUser = useCallback((nextUser: User | null) => {
    if (activeUserId.current !== (nextUser?.id ?? null)) {
      resetUserProfileCache(nextUser?.id ?? null);
      queryClient.clear();
      activeUserId.current = nextUser?.id ?? null;
    }
    setUser(nextUser);
  }, []);

  const refreshUser = useCallback(async () => {
    const revision = session.current;
    const request = ++currentUserRequest.current;
    try {
      const currentUser = await authApi.getCurrentUser();
      if (revision !== session.current || request !== currentUserRequest.current) return null;
      applyUser(currentUser);
      return currentUser;
    } catch {
      if (revision === session.current && request === currentUserRequest.current) applyUser(null);
      return null;
    }
  }, [applyUser]);

  useEffect(() => {
    const revision = session.current;
    void refreshUser().finally(() => {
      if (revision === session.current) setIsLoading(false);
    });
  }, [refreshUser]);

  useEffect(() => {
    const syncSession = (event: StorageEvent) => {
      if (event.key !== SESSION_CHANGED_KEY) return;
      const revision = ++session.current;
      applyUser(null);
      setIsLoading(true);
      void refreshUser().finally(() => {
        if (revision === session.current) setIsLoading(false);
      });
    };
    window.addEventListener('storage', syncSession);
    return () => window.removeEventListener('storage', syncSession);
  }, [applyUser, refreshUser]);

  const changeUser = useCallback(async <T extends { user: User | null },>(action: () => Promise<T>) => {
    return changeApiSession(async () => {
      session.current += 1;
      const response = await action();
      session.current += 1;
      applyUser(response.user);
      setIsLoading(false);
      try {
        localStorage.setItem(SESSION_CHANGED_KEY, String(Date.now()));
      } catch {
        // The current tab still updates when browser storage is unavailable.
      }
      return response;
    });
  }, [applyUser]);

  const login = useCallback(async (credentials: LoginCredentials) => {
    await changeUser(() => authApi.login(credentials));
  }, [changeUser]);
  const register = useCallback(async (data: RegisterData) => {
    const response = await changeUser(() => authApi.register(data));
    return response.verification_email_sent;
  }, [changeUser]);
  const logout = useCallback(async () => {
    await changeUser(async () => {
      await authApi.logout();
      return { user: null };
    });
  }, [changeUser]);

  const sendVerificationEmail = useCallback(async () => {
    await authApi.sendVerificationEmail();
  }, []);

  const resendVerificationEmail = useCallback(async () => {
    await authApi.resendVerificationEmail();
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isEmailVerified: user?.email_verified ?? false,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
        sendVerificationEmail,
        resendVerificationEmail,
      }}
    >
      <Fragment key={user?.id ?? 'guest'}>{children}</Fragment>
    </AuthContext.Provider>
  );
}

export default AuthContext;
