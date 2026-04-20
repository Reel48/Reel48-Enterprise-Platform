'use client';

import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import {
  getCurrentUser,
  fetchAuthSession,
  signIn as amplifySignIn,
  signOut as amplifySignOut,
} from 'aws-amplify/auth';

import type { AuthState, AuthUser, TenantContext, UserRole } from '@/types/auth';
import { api } from '@/lib/api/client';

export interface AuthContextValue {
  user: AuthUser | null;
  authState: AuthState;
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

// TODO: Remove legacy role mapping once all dev Cognito users have been
// re-attributed to the 4-role model (reel48_admin, company_admin, manager, employee).
function normalizeRole(rawRole: string): UserRole {
  switch (rawRole) {
    case 'reel48_admin':
    case 'company_admin':
    case 'manager':
    case 'employee':
      return rawRole;
    case 'corporate_admin':
    case 'sub_brand_admin':
      return 'company_admin';
    case 'regional_manager':
      return 'manager';
    default:
      return 'employee';
  }
}

function extractTenantContext(
  userId: string,
  payload: Record<string, unknown>,
): TenantContext {
  const companyId = (payload['custom:company_id'] as string) || null;
  const role = normalizeRole((payload['custom:role'] as string) || 'employee');

  return { userId, companyId, role };
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authState, setAuthState] = useState<AuthState>('loading');

  const loadSession = useCallback(async () => {
    try {
      const currentUser = await getCurrentUser();
      const session = await fetchAuthSession();
      const idToken = session.tokens?.idToken;

      if (!idToken) {
        setUser(null);
        setAuthState('unauthenticated');
        return;
      }

      const payload = idToken.payload as Record<string, unknown>;
      const tenantContext = extractTenantContext(
        currentUser.userId,
        payload,
      );

      const email = (payload['email'] as string) || '';
      const fullName = (payload['name'] as string) || email;

      // Set initial user state so the app is usable immediately
      setUser({
        email,
        fullName,
        companyName: tenantContext.role === 'reel48_admin' ? 'Reel48+' : '',
        tenantContext,
      });
      setAuthState('authenticated');

      // Fetch company name from API (non-blocking)
      if (tenantContext.role !== 'reel48_admin') {
        try {
          const response = await api.get<{ companyName?: string }>('/api/v1/users/me');
          const apiCompanyName = response.data?.companyName || '';
          if (apiCompanyName) {
            setUser((prev) =>
              prev ? { ...prev, companyName: apiCompanyName } : prev,
            );
          }
        } catch {
          // Company name fetch failed — keep empty string fallback
        }
      }
    } catch {
      setUser(null);
      setAuthState('unauthenticated');
    }
  }, []);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      await amplifySignIn({ username: email, password });
      await loadSession();
    },
    [loadSession],
  );

  const signOut = useCallback(async () => {
    await amplifySignOut();
    try {
      localStorage.removeItem('reel48_cart');
    } catch {
      // Storage unavailable — ignore
    }
    setUser(null);
    setAuthState('unauthenticated');
  }, []);

  const refreshSession = useCallback(async () => {
    await fetchAuthSession({ forceRefresh: true });
    await loadSession();
  }, [loadSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      authState,
      isAuthenticated: authState === 'authenticated',
      isLoading: authState === 'loading',
      signIn,
      signOut,
      refreshSession,
    }),
    [user, authState, signIn, signOut, refreshSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
