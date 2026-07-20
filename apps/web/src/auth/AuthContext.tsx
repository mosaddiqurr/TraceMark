import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, setCsrfToken } from "../api/client";
import type { SessionResponse, User } from "../api/types";

type AuthState = {
  user: User | null;
  loading: boolean;
  login(email: string, password: string): Promise<void>;
  register(displayName: string, email: string, password: string): Promise<void>;
  logout(): Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api<SessionResponse>("/auth/session")
      .then((session) => { setUser(session.user); setCsrfToken(session.csrf_token); })
      .catch(() => { setUser(null); setCsrfToken(null); })
      .finally(() => setLoading(false));
  }, []);
  const applySession = useCallback((session: SessionResponse) => {
    setUser(session.user);
    setCsrfToken(session.csrf_token);
  }, []);
  const login = useCallback(async (email: string, password: string) => applySession(await api<SessionResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) })), [applySession]);
  const register = useCallback(async (display_name: string, email: string, password: string) => applySession(await api<SessionResponse>("/auth/register", { method: "POST", body: JSON.stringify({ display_name, email, password }) })), [applySession]);
  const logout = useCallback(async () => { await api<void>("/auth/session", { method: "DELETE" }); setUser(null); setCsrfToken(null); }, []);
  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
