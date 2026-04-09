'use client';

import { useCallback, useMemo, useState } from 'react';
import { Loading } from '@carbon/react';

import {
  usePlatformOverview,
  useRevenueByCompany,
  usePlatformRevenueOverTime,
  usePlatformOrderBreakdown,
  usePlatformTopProducts,
  usePlatformInvoiceSummary,
  usePlatformApprovalMetrics,
} from '@/hooks/usePlatformAnalytics';
import {
  ApprovalMetricsCards,
  DateRangeFilter,
  InvoiceSummaryCards,
  OrderStatusBreakdown,
  PlatformOverviewCards,
  RevenueByCompanyTable,
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

export default function PlatformAnalyticsPage() {
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

  const overview = usePlatformOverview();
  const revenueByCompany = useRevenueByCompany(startDate, endDate);
  const revenueOverTime = usePlatformRevenueOverTime(startDate, endDate);
  const orderBreakdown = usePlatformOrderBreakdown(startDate, endDate);
  const topProducts = usePlatformTopProducts(startDate, endDate);
  const invoiceSummary = usePlatformInvoiceSummary(startDate, endDate);
  const approvalMetrics = usePlatformApprovalMetrics(startDate, endDate);

  return (
    <div>
      <div className="flex flex-col gap-4 mb-8 sm:flex-row sm:items-end sm:justify-between">
        <h1 className="text-3xl font-semibold">Platform Analytics</h1>
        <DateRangeFilter
          onDateChange={handleDateChange}
          defaultStartDate={defaults.start}
          defaultEndDate={defaults.end}
        />
      </div>

      {/* Platform Overview KPI Cards */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Platform Overview</h2>
        {overview.isLoading ? (
          <Loading withOverlay={false} small description="Loading overview..." />
        ) : overview.data ? (
          <PlatformOverviewCards data={overview.data} />
        ) : null}
      </section>

      {/* Revenue by Company */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Revenue by Company</h2>
        {revenueByCompany.isLoading ? (
          <Loading withOverlay={false} small description="Loading revenue data..." />
        ) : revenueByCompany.data ? (
          <RevenueByCompanyTable data={revenueByCompany.data} />
        ) : null}
      </section>

      {/* Revenue Over Time Chart */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Revenue Over Time</h2>
        {revenueOverTime.isLoading ? (
          <Loading withOverlay={false} small description="Loading trend data..." />
        ) : revenueOverTime.data ? (
          <SpendOverTimeChart data={revenueOverTime.data} title="Revenue Over Time" />
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

      {/* Top Products */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Top Products (Platform-Wide)</h2>
        {topProducts.isLoading ? (
          <Loading withOverlay={false} small description="Loading product data..." />
        ) : topProducts.data ? (
          <TopProductsTable data={topProducts.data} />
        ) : null}
      </section>

      {/* Invoice Summary */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Invoice Summary</h2>
        {invoiceSummary.isLoading ? (
          <Loading withOverlay={false} small description="Loading invoice data..." />
        ) : invoiceSummary.data ? (
          <InvoiceSummaryCards data={invoiceSummary.data} />
        ) : null}
      </section>

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
