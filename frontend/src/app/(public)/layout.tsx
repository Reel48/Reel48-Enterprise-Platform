'use client';

import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/lib/auth/hooks';

export default function PublicLayout({ children }: { children: ReactNode }) {
  const { authState } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (authState === 'authenticated') {
      router.replace('/dashboard');
    }
  }, [authState, router]);

  if (authState === 'authenticated') {
    return null;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-page">
      {children}
    </div>
  );
}
