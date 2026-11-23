import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { get, post, UNAUTHORIZED_EVENT, type User } from "./api";

interface AuthStatus { setup_required: boolean; user: User | null; min_password_length: number }

interface AuthContextValue {
  state: "loading" | "error" | "ready";
  error: string | null;
  user: User | null;
  setupRequired: boolean;
  minPasswordLength: number;
  login: (username: string, password: string) => Promise<void>;
  setup: (username: string, displayName: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  sessionExpired: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setStatus(await get<AuthStatus>("/auth/status"));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const expired = () => {
      setStatus((current) => {
        if (current?.user) setSessionExpired(true);
        return current ? { ...current, user: null } : current;
      });
    };
    window.addEventListener(UNAUTHORIZED_EVENT, expired);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, expired);
  }, [refresh]);

  const login = async (username: string, password: string) => {
    const { user } = await post<{ user: User }>("/auth/login", { username, password });
    setSessionExpired(false);
    setStatus((current) => ({ setup_required: false, min_password_length: current?.min_password_length ?? 10, user }));
  };

  const setup = async (username: string, displayName: string, password: string) => {
    const { user } = await post<{ user: User }>("/auth/setup", { username, display_name: displayName, password });
    setStatus((current) => ({ setup_required: false, min_password_length: current?.min_password_length ?? 10, user }));
  };

  const logout = async () => {
    await post("/auth/logout").catch(() => undefined);
    setSessionExpired(false);
    setStatus((current) => (current ? { ...current, user: null } : current));
  };

  const value: AuthContextValue = {
    state: error && !status ? "error" : status ? "ready" : "loading",
    error,
    user: status?.user ?? null,
    setupRequired: status?.setup_required ?? false,
    minPasswordLength: status?.min_password_length ?? 10,
    login, setup, logout, refresh, sessionExpired,
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
