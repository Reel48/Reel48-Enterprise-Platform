'use client';

import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { Loading } from '@carbon/react';

import type { UserRole } from '@/types/auth';
import { useAuth } from '@/lib/auth/hooks';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRoles?: UserRole[];
}

export function ProtectedRoute({ children, requiredRoles }: ProtectedRouteProps) {
  const { authState, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (authState === 'unauthenticated') {
      router.replace('/login');
    }
  }, [authState, router]);

  if (authState === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loading withOverlay={false} description="Loading..." />
      </div>
    );
  }

  if (authState === 'unauthenticated') {
    return null;
  }

  if (requiredRoles && user && !requiredRoles.includes(user.tenantContext.role)) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center">
          <h1 className="text-2xl font-semibold text-text-primary">
            Access Denied
          </h1>
          <p className="text-text-secondary">
            You do not have permission to access this page.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
