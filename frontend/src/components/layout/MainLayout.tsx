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
          className="px-8 pb-8 pt-10"
          style={{
            marginLeft: '256px',
            paddingTop: 'calc(48px + 2.5rem)',
            minHeight: '100vh',
          }}
        >
          {children}
        </main>
      </Theme>
    </>
  );
}
