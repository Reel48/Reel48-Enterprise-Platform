'use client';

import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type {
  ApprovalMetrics,
  CompanyRevenue,
  InvoiceSummary,
  OrderStatusBreakdown,
  PlatformOverview,
  SpendOverTime,
  TopProduct,
} from '@/types/analytics';

function buildDateParams(startDate?: string, endDate?: string): Record<string, string> {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  return params;
}

export function usePlatformOverview() {
  return useQuery({
    queryKey: ['platform-analytics', 'overview'],
    queryFn: async () => {
      const res = await api.get<PlatformOverview>(
        '/api/v1/platform/analytics/overview',
      );
      return res.data;
    },
  });
}

export function useRevenueByCompany(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['platform-analytics', 'revenue-by-company', startDate, endDate],
    queryFn: async () => {
      const res = await api.get<CompanyRevenue[]>(
        '/api/v1/platform/analytics/revenue/by-company',
        buildDateParams(startDate, endDate),
      );
      return res.data;
    },
  });
}

export function usePlatformRevenueOverTime(
  startDate?: string,
  endDate?: string,
  granularity: string = 'month',
) {
  return useQuery({
    queryKey: ['platform-analytics', 'revenue-over-time', startDate, endDate, granularity],
    queryFn: async () => {
      const params = { ...buildDateParams(startDate, endDate), granularity };
      const res = await api.get<SpendOverTime[]>(
        '/api/v1/platform/analytics/revenue/over-time',
        params,
      );
      return res.data;
    },
  });
}

export function usePlatformOrderBreakdown(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['platform-analytics', 'order-breakdown', startDate, endDate],
    queryFn: async () => {
      const res = await api.get<OrderStatusBreakdown[]>(
        '/api/v1/platform/analytics/orders/status-breakdown',
        buildDateParams(startDate, endDate),
      );
      return res.data;
    },
  });
}

export function usePlatformTopProducts(
  startDate?: string,
  endDate?: string,
  limit: number = 10,
) {
  return useQuery({
    queryKey: ['platform-analytics', 'top-products', startDate, endDate, limit],
    queryFn: async () => {
      const params = { ...buildDateParams(startDate, endDate), limit: String(limit) };
      const res = await api.get<TopProduct[]>(
        '/api/v1/platform/analytics/orders/top-products',
        params,
      );
      return res.data;
    },
  });
}

export function usePlatformInvoiceSummary(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['platform-analytics', 'invoice-summary', startDate, endDate],
    queryFn: async () => {
      const res = await api.get<InvoiceSummary>(
        '/api/v1/platform/analytics/invoices/summary',
        buildDateParams(startDate, endDate),
      );
      return res.data;
    },
  });
}

export function usePlatformApprovalMetrics(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['platform-analytics', 'approval-metrics', startDate, endDate],
    queryFn: async () => {
      const res = await api.get<ApprovalMetrics>(
        '/api/v1/platform/analytics/approvals/metrics',
        buildDateParams(startDate, endDate),
      );
      return res.data;
    },
  });
}
