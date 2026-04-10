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

function extractTenantContext(
  userId: string,
  payload: Record<string, unknown>,
): TenantContext {
  const companyId = (payload['custom:company_id'] as string) || null;
  const subBrandId = (payload['custom:sub_brand_id'] as string) || null;
  const role = (payload['custom:role'] as UserRole) || 'employee';

  return { userId, companyId, subBrandId, role };
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

      const companyName =
        (payload['custom:company_name'] as string) ||
        (tenantContext.role === 'reel48_admin' ? 'Reel48+' : '');

      setUser({
        email: (payload['email'] as string) || '',
        fullName: (payload['name'] as string) || (payload['email'] as string) || '',
        companyName,
        tenantContext,
      });
      setAuthState('authenticated');
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
