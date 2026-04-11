'use client';

import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/lib/auth/hooks';
import { ProtectedRoute } from '@/components/features/auth/ProtectedRoute';
import { MainLayout } from '@/components/layout/MainLayout';
import { CartProvider } from '@/lib/cart/CartContext';

export default function AuthenticatedLayout({
  children,
}: {
  children: ReactNode;
}) {
  const { user } = useAuth();
  const router = useRouter();

  const isReel48Admin = user?.tenantContext.role === 'reel48_admin';

  useEffect(() => {
    if (isReel48Admin) {
      router.replace('/platform/dashboard');
    }
  }, [isReel48Admin, router]);

  if (isReel48Admin) return null;

  return (
    <ProtectedRoute>
      <CartProvider>
        <MainLayout>{children}</MainLayout>
      </CartProvider>
    </ProtectedRoute>
  );
}
