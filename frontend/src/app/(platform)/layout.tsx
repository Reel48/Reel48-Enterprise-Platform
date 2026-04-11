'use client';

import type { ReactNode } from 'react';

import { ProtectedRoute } from '@/components/features/auth/ProtectedRoute';
import { MainLayout } from '@/components/layout/MainLayout';
import { CartProvider } from '@/lib/cart/CartContext';

export default function PlatformLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <ProtectedRoute requiredRoles={['reel48_admin']}>
      <CartProvider>
        <MainLayout>{children}</MainLayout>
      </CartProvider>
    </ProtectedRoute>
  );
}
