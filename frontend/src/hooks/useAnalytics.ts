'use client';

import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type {
  ApprovalMetrics,
  InvoiceSummary,
  OrderStatusBreakdown,
  SizeDistribution,
  SpendOverTime,
  SpendSummary,
  SubBrandSpend,
  TopProduct,
} from '@/types/analytics';

function buildDateParams(startDate?: string, endDate?: string): Record<string, string> {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  return params;
}

export function useSpendSummary(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['analytics', 'spend-summary', startDate, endDate],
    queryFn: async () => {
      const res = await api.get<SpendSummary>(
        '/api/v1/analytics/spend/summary',
        buildDateParams(startDate, endDate),
      );
      return res.data;
    },
  });
}

export function useSpendBySubBrand(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['analytics', 'spend-by-sub-brand', startDate, endDate],
    queryFn: async () => {
      const res = await api.get<SubBrandSpend[]>(
        '/api/v1/analytics/spend/by-sub-brand',
        buildDateParams(startDate, endDate),
      );
      return res.data;
    },
  });
}

export function useSpendOverTime(
  startDate?: string,
  endDate?: string,
  granularity: string = 'month',
) {
  return useQuery({
    queryKey: ['analytics', 'spend-over-time', startDate, endDate, granularity],
    queryFn: async () => {
      const params = { ...buildDateParams(startDate, endDate), granularity };
      const res = await api.get<SpendOverTime[]>(
        '/api/v1/analytics/spend/over-time',
        params,
      );
      return res.data;
    },
  });
}

export function useTopProducts(
  startDate?: string,
  endDate?: string,
  limit: number = 10,
) {
  return useQuery({
    queryKey: ['analytics', 'top-products', startDate, endDate, limit],
    queryFn: async () => {
      const params = { ...buildDateParams(startDate, endDate), limit: String(limit) };
      const res = await api.get<TopProduct[]>(
        '/api/v1/analytics/orders/top-products',
        params,
      );
      return res.data;
    },
  });
}

export function useOrderStatusBreakdown(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['analytics', 'order-status-breakdown', startDate, endDate],
    queryFn: async () => {
      const res = await api.get<OrderStatusBreakdown[]>(
        '/api/v1/analytics/orders/status-breakdown',
        buildDateParams(startDate, endDate),
      );
      return res.data;
    },
  });
}

export function useSizeDistribution(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['analytics', 'size-distribution', startDate, endDate],
    queryFn: async () => {
      const res = await api.get<SizeDistribution[]>(
        '/api/v1/analytics/orders/size-distribution',
        buildDateParams(startDate, endDate),
      );
      return res.data;
    },
  });
}

export function useInvoiceSummary(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['analytics', 'invoice-summary', startDate, endDate],
    queryFn: async () => {
      const res = await api.get<InvoiceSummary>(
        '/api/v1/analytics/invoices/summary',
        buildDateParams(startDate, endDate),
      );
      return res.data;
    },
  });
}

export function useApprovalMetrics(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['analytics', 'approval-metrics', startDate, endDate],
    queryFn: async () => {
      const res = await api.get<ApprovalMetrics>(
        '/api/v1/analytics/approvals/metrics',
        buildDateParams(startDate, endDate),
      );
      return res.data;
    },
  });
}
