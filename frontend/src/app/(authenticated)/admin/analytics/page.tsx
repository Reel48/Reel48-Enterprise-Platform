'use client';

import { InlineNotification, Loading, Tile } from '@carbon/react';
import { UserMultiple } from '@carbon/react/icons';

import { useAuth } from '@/lib/auth/hooks';
import type { UserRole } from '@/types/auth';
import { useCompanyOverview } from '@/hooks/useAnalytics';

const ANALYTICS_ROLES: UserRole[] = ['company_admin'];

export default function ClientAnalyticsPage() {
  const { user } = useAuth();
  const role = user?.tenantContext.role;

  const overview = useCompanyOverview();

  if (!role || !ANALYTICS_ROLES.includes(role)) {
    return (
      <div className="mt-8">
        <InlineNotification
          kind="error"
          title="Access Denied"
          subtitle="You do not have permission to view analytics."
          lowContrast
          hideCloseButton
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-3xl font-semibold">Analytics</h1>

      <section>
        <h2 className="text-xl font-semibold mb-4">Overview</h2>
        {overview.isLoading ? (
          <Loading withOverlay={false} small description="Loading overview..." />
        ) : overview.data ? (
          <Tile>
            <div className="flex items-start gap-3">
              <UserMultiple size={24} className="text-interactive mt-0.5 shrink-0" />
              <div>
                <p className="text-sm text-text-secondary mb-1">Active Users</p>
                <p className="text-2xl font-semibold">
                  {overview.data.activeUsers.toLocaleString()}
                </p>
              </div>
            </div>
          </Tile>
        ) : null}
      </section>

      <InlineNotification
        kind="info"
        title="More analytics coming soon"
        subtitle="Detailed spend, order, and engagement reporting will return once the Shopify integration lands."
        lowContrast
        hideCloseButton
      />
    </div>
  );
}
