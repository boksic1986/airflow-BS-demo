import {createContext, useContext, useEffect, useMemo, useState, type ReactNode} from "react";

import {ApiError, getSession, login as requestLogin, logout as requestLogout, type SessionUser, type UserRole} from "../../api";
import {errorMessage} from "../../lib/errors";

type SessionContextValue = {
  user: SessionUser | null;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (role: UserRole) => boolean;
};

const SessionContext = createContext<SessionContextValue>({
  user: null,
  loading: true,
  error: null,
  login: async () => undefined,
  logout: async () => undefined,
  hasRole: () => false,
});

const ranks: Record<UserRole, number> = {viewer: 1, operator: 2, admin: 3};

export function SessionProvider({children}: {children: ReactNode}) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    getSession()
      .then((current) => { if (!disposed) setUser(current); })
      .catch((loadError) => {
        if (!disposed && !(loadError instanceof ApiError && loadError.status === 401)) setError(errorMessage(loadError));
      })
      .finally(() => { if (!disposed) setLoading(false); });
    return () => { disposed = true; };
  }, []);

  const value = useMemo<SessionContextValue>(() => ({
    user,
    loading,
    error,
    login: async (username, password) => {
      setError(null);
      const current = await requestLogin({username, password});
      setUser(current);
    },
    logout: async () => {
      await requestLogout();
      setUser(null);
    },
    hasRole: (role) => Boolean(user && ranks[user.role] >= ranks[role]),
  }), [error, loading, user]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  return useContext(SessionContext);
}
