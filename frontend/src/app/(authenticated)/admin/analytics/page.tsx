'use client';

import { useCallback, useMemo, useState } from 'react';
import { InlineNotification, Loading } from '@carbon/react';

import { useAuth } from '@/lib/auth/hooks';
import type { UserRole } from '@/types/auth';
import {
  useSpendSummary,
  useSpendBySubBrand,
  useSpendOverTime,
  useTopProducts,
  useOrderStatusBreakdown,
  useSizeDistribution,
  useInvoiceSummary,
  useApprovalMetrics,
} from '@/hooks/useAnalytics';
import {
  ApprovalMetricsCards,
  DateRangeFilter,
  InvoiceSummaryCards,
  OrderStatusBreakdown,
  SizeDistribution,
  SpendBySubBrandTable,
  SpendKPICards,
  SpendOverTimeChart,
  TopProductsTable,
} from '@/components/features/analytics';

function getDefaultDateRange(): { start: Date; end: Date } {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  return { start, end };
}

function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const ANALYTICS_ROLES: UserRole[] = [
  'corporate_admin',
  'sub_brand_admin',
  'regional_manager',
];

export default function ClientAnalyticsPage() {
  const { user } = useAuth();
  const role = user?.tenantContext.role;

  const defaults = useMemo(() => getDefaultDateRange(), []);
  const [startDate, setStartDate] = useState<string | undefined>(formatDate(defaults.start));
  const [endDate, setEndDate] = useState<string | undefined>(formatDate(defaults.end));

  const handleDateChange = useCallback(
    (start: string | undefined, end: string | undefined) => {
      setStartDate(start);
      setEndDate(end);
    },
    [],
  );

  const isCorporateAdmin = role === 'corporate_admin';

  const spendSummary = useSpendSummary(startDate, endDate);
  const spendBySubBrand = useSpendBySubBrand(startDate, endDate);
  const spendOverTime = useSpendOverTime(startDate, endDate);
  const topProducts = useTopProducts(startDate, endDate);
  const orderBreakdown = useOrderStatusBreakdown(startDate, endDate);
  const sizeDistribution = useSizeDistribution(startDate, endDate);
  const invoiceSummary = useInvoiceSummary(startDate, endDate);
  const approvalMetrics = useApprovalMetrics(startDate, endDate);

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
    <div>
      <div className="flex flex-col gap-4 mb-8 sm:flex-row sm:items-end sm:justify-between">
        <h1 className="text-3xl font-semibold">Analytics</h1>
        <DateRangeFilter
          onDateChange={handleDateChange}
          defaultStartDate={defaults.start}
          defaultEndDate={defaults.end}
        />
      </div>

      {/* Spend Summary KPI Cards */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Spend Summary</h2>
        {spendSummary.isLoading ? (
          <Loading withOverlay={false} small description="Loading spend summary..." />
        ) : spendSummary.data ? (
          <SpendKPICards data={spendSummary.data} />
        ) : null}
      </section>

      {/* Spend by Sub-Brand (corporate_admin only) */}
      {isCorporateAdmin && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Spend by Sub-Brand</h2>
          {spendBySubBrand.isLoading ? (
            <Loading withOverlay={false} small description="Loading sub-brand data..." />
          ) : spendBySubBrand.data ? (
            <SpendBySubBrandTable data={spendBySubBrand.data} />
          ) : null}
        </section>
      )}

      {/* Spend Over Time Chart */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Spend Over Time</h2>
        {spendOverTime.isLoading ? (
          <Loading withOverlay={false} small description="Loading trend data..." />
        ) : spendOverTime.data ? (
          <SpendOverTimeChart data={spendOverTime.data} />
        ) : null}
      </section>

      {/* Top Products */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Top Products</h2>
        {topProducts.isLoading ? (
          <Loading withOverlay={false} small description="Loading product data..." />
        ) : topProducts.data ? (
          <TopProductsTable data={topProducts.data} />
        ) : null}
      </section>

      {/* Order Status Breakdown */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Order Status Breakdown</h2>
        {orderBreakdown.isLoading ? (
          <Loading withOverlay={false} small description="Loading order data..." />
        ) : orderBreakdown.data ? (
          <OrderStatusBreakdown data={orderBreakdown.data} />
        ) : null}
      </section>

      {/* Size Distribution */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Size Distribution</h2>
        {sizeDistribution.isLoading ? (
          <Loading withOverlay={false} small description="Loading size data..." />
        ) : sizeDistribution.data ? (
          <SizeDistribution data={sizeDistribution.data} />
        ) : null}
      </section>

      {/* Invoice Summary (corporate_admin only) */}
      {isCorporateAdmin && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Invoice Summary</h2>
          {invoiceSummary.isLoading ? (
            <Loading withOverlay={false} small description="Loading invoice data..." />
          ) : invoiceSummary.data ? (
            <InvoiceSummaryCards data={invoiceSummary.data} />
          ) : null}
        </section>
      )}

      {/* Approval Metrics */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Approval Metrics</h2>
        {approvalMetrics.isLoading ? (
          <Loading withOverlay={false} small description="Loading approval data..." />
        ) : approvalMetrics.data ? (
          <ApprovalMetricsCards data={approvalMetrics.data} />
        ) : null}
      </section>
    </div>
  );
}
