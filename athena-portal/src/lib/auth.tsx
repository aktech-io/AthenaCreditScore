import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getToken, setToken as storeToken, clearAuth, getCustomerId, setCustomerId as storeCustomerId } from "./api";

interface AuthState {
  token: string | null;
  roles: string[];
  customerId: number | null;
}

interface AuthContextValue extends AuthState {
  isAuthenticated: boolean;
  isAdmin: boolean;
  isCustomer: boolean;
  login: (token: string, roles: string[], customerId?: number) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function parseRolesFromToken(token: string): string[] {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.roles || payload.role || [];
  } catch {
    return [];
  }
}

function parseCustomerIdFromToken(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.customerId ?? payload.customer_id ?? null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(() => {
    const token = getToken();
    if (!token) return { token: null, roles: [], customerId: null };
    const roles = parseRolesFromToken(token);
    const customerId = getCustomerId() ?? parseCustomerIdFromToken(token);
    return { token, roles, customerId };
  });

  const login = useCallback((token: string, roles: string[], customerId?: number) => {
    storeToken(token);
    const cid = customerId ?? parseCustomerIdFromToken(token);
    if (cid) storeCustomerId(cid);
    setState({ token, roles, customerId: cid });
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setState({ token: null, roles: [], customerId: null });
  }, []);

  const isAuthenticated = !!state.token;
  const isAdmin = state.roles.some((r) => ["ADMIN", "ROLE_ADMIN", "SUPER_ADMIN"].includes(r.toUpperCase()));
  const isCustomer = state.roles.some((r) => ["CUSTOMER", "ROLE_CUSTOMER"].includes(r.toUpperCase()));

  return (
    <AuthContext.Provider value={{ ...state, isAuthenticated, isAdmin, isCustomer, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
