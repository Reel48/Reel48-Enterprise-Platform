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
        <main
          className="p-6"
          style={{
            marginLeft: '256px',
            paddingTop: '48px',
            minHeight: '100vh',
          }}
        >
          {children}
        </main>
      </Theme>
    </>
  );
}
