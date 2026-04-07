'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loading } from '@carbon/react';

import { useAuth } from '@/lib/auth/hooks';

export default function RootPage() {
  const { authState } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (authState === 'authenticated') {
      router.replace('/dashboard');
    } else if (authState === 'unauthenticated') {
      router.replace('/login');
    }
  }, [authState, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Loading withOverlay={false} description="Loading..." />
    </div>
  );
}
