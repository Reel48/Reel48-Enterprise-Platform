'use client';

import { useContext, useEffect } from 'react';
import { useRouter } from 'next/navigation';

import type { TenantContext, UserRole } from '@/types/auth';
import { AuthContext } from './context';
import type { AuthContextValue } from './context';

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function useTenantContext(): TenantContext {
  const { user } = useAuth();
  if (!user) {
    throw new Error(
      'useTenantContext must be used when the user is authenticated',
    );
  }
  return user.tenantContext;
}

export function useRequireAuth(): AuthContextValue {
  const auth = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (auth.authState === 'unauthenticated') {
      router.replace('/login');
    }
  }, [auth.authState, router]);

  return auth;
}

export function useHasRole(roles: UserRole[]): boolean {
  const { user } = useAuth();
  if (!user) return false;
  return roles.includes(user.tenantContext.role);
}
