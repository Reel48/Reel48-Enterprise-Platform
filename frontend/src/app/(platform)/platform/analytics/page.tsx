'use client';

import { InlineNotification, Loading } from '@carbon/react';

import { usePlatformOverview } from '@/hooks/usePlatformAnalytics';
import { PlatformOverviewCards } from '@/components/features/analytics';

export default function PlatformAnalyticsPage() {
  const overview = usePlatformOverview();

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-3xl font-semibold">Platform Analytics</h1>

      <section>
        <h2 className="text-xl font-semibold mb-4">Platform Overview</h2>
        {overview.isLoading ? (
          <Loading withOverlay={false} small description="Loading overview..." />
        ) : overview.data ? (
          <PlatformOverviewCards data={overview.data} />
        ) : null}
      </section>

      <InlineNotification
        kind="info"
        title="More analytics coming soon"
        subtitle="Cross-company revenue and engagement reporting will return once the Shopify integration lands."
        lowContrast
        hideCloseButton
      />
    </div>
  );
}
