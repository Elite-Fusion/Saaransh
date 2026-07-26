import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

const STORAGE_KEY_ACCESS = "saaransh_access_token";
const STORAGE_KEY_REFRESH = "saaransh_refresh_token";

function loadTokens() {
  return {
    access: localStorage.getItem(STORAGE_KEY_ACCESS),
    refresh: localStorage.getItem(STORAGE_KEY_REFRESH),
  };
}

function saveTokens(access, refresh) {
  localStorage.setItem(STORAGE_KEY_ACCESS, access);
  localStorage.setItem(STORAGE_KEY_REFRESH, refresh);
}

function clearTokens() {
  localStorage.removeItem(STORAGE_KEY_ACCESS);
  localStorage.removeItem(STORAGE_KEY_REFRESH);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const me = await api.get("/auth/me");
      setUser(me);
    } catch {
      setUser(null);
      clearTokens();
    }
  }, []);

  // On mount, check for existing tokens and load user
  useEffect(() => {
    const { access } = loadTokens();
    if (access) {
      fetchUser().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [fetchUser]);

  const login = async (email, password) => {
    const tokens = await api.post("/auth/login", { email, password });
    saveTokens(tokens.access_token, tokens.refresh_token);
    await fetchUser();
  };

  const logout = async () => {
    try {
      const { refresh } = loadTokens();
      if (refresh) {
        await api.post("/auth/logout", { refresh_token: refresh }).catch(() => {});
      }
    } finally {
      clearTokens();
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
