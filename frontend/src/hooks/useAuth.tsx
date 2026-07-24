import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, getToken, setToken } from "../lib/api";
import { supabase } from "../lib/supabase";
import type { TokenResponse, UserProfile } from "../lib/types";

interface AuthContextValue {
  user: UserProfile | null;
  loading: boolean;
  loginWithEmail: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  loginAsGuest: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    api.get<UserProfile>("/auth/profile")
      .then(({ data }) => {
        setUser(data);
      })
      .catch(() => {
        setToken(null);
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const loginWithEmail = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<TokenResponse>("/auth/login", { email, password });
    setToken(data.access_token);
    setUser(data.user);
  }, []);

  const loginWithGoogle = useCallback(async () => {
    if (!supabase) {
      throw new Error("Google login is not configured (set VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY).");
    }
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
  }, []);

  const loginAsGuest = useCallback(async () => {
    const { data } = await api.post<TokenResponse>("/auth/guest");
    setToken(data.access_token);
    setUser(data.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // Best-effort; local sign-out always proceeds.
    }
    if (supabase) {
      await supabase.auth.signOut().catch(() => undefined);
    }
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, loginWithEmail, loginWithGoogle, loginAsGuest, logout }),
    [user, loading, loginWithEmail, loginWithGoogle, loginAsGuest, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
