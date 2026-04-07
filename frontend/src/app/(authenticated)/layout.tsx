'use client';

import type { ReactNode } from 'react';

import { ProtectedRoute } from '@/components/features/auth/ProtectedRoute';
import { MainLayout } from '@/components/layout/MainLayout';

export default function AuthenticatedLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <ProtectedRoute>
      <MainLayout>{children}</MainLayout>
    </ProtectedRoute>
  );
}
