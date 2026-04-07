import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Providers } from './providers';
import './globals.scss';

export const metadata: Metadata = {
  title: 'Reel48+',
  description: 'Enterprise apparel management platform',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <ErrorBoundary>{children}</ErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
