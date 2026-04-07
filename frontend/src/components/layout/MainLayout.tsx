'use client';

import type { ReactNode } from 'react';
import { Theme } from '@carbon/react';

import { Header } from './Header';
import { Sidebar } from './Sidebar';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <>
      <Header />
      <Sidebar />
      <Theme theme="g10">
        <main className="cds--content p-6">{children}</main>
      </Theme>
    </>
  );
}
