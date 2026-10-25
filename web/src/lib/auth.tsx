"use client";

import * as React from "react";
import { api, refreshSession, setAccessToken, setOnAuthLost, unwrap, type Schemas } from "./api";

export type Me = Schemas["Me"];
export type Role = Me["role"];

type AuthState =
  | { status: "loading"; me: null }
  | { status: "anonymous"; me: null }
  | { status: "authenticated"; me: Me };

type AuthContextValue = AuthState & {
  startSession: (accessToken: string) => Promise<Me>;
  reloadMe: () => Promise<void>;
  switchRole: (roleId: string) => Promise<Me>;
  logout: () => Promise<void>;
};

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function homeFor(role: Role): string {
  switch (role) {
    case "PLATFORM_ADMIN":
      return "/app/platform";
    case "SCHOOL_ADMIN":
      return "/app/admin";
    case "PRINCIPAL":
      return "/app/principal";
    case "TEACHER":
      return "/app/teacher";
    default:
      return "/app/family";
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState<AuthState>({ status: "loading", me: null });

  const loadMe = React.useCallback(async (): Promise<Me> => {
    const me = await unwrap(api.GET("/api/v1/me"));
    setState({ status: "authenticated", me });
    return me;
  }, []);

  React.useEffect(() => {
    setOnAuthLost(() => {
      setAccessToken(null);
      setState({ status: "anonymous", me: null });
    });
    // Restore the session from the httpOnly refresh cookie, if any.
    refreshSession().then(async (ok) => {
      if (!ok) {
        setState({ status: "anonymous", me: null });
        return;
      }
      try {
        await loadMe();
      } catch {
        setState({ status: "anonymous", me: null });
      }
    });
    return () => setOnAuthLost(null);
  }, [loadMe]);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      ...state,
      startSession: async (accessToken) => {
        setAccessToken(accessToken);
        return loadMe();
      },
      reloadMe: async () => {
        await loadMe();
      },
      switchRole: async (roleId) => {
        const tokens = await unwrap(
          api.POST("/api/v1/auth/switch", { body: { role_id: roleId, client: "web" } }),
        );
        setAccessToken(tokens.access_token);
        return loadMe();
      },
      logout: async () => {
        await api.POST("/api/v1/auth/logout", { body: {} });
        setAccessToken(null);
        setState({ status: "anonymous", me: null });
      },
    }),
    [state, loadMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

/** The signed-in user; only call inside the /app layout (which guarantees a session). */
export function useMe(): Me {
  const auth = useAuth();
  if (auth.status !== "authenticated") throw new Error("Not signed in");
  return auth.me;
}
