import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type { Company } from '@/types/companies';
import type { Catalog } from '@/types/catalogs';
import type { Order } from '@/types/orders';
import type { InvoiceSummary } from '@/types/invoices';
import type { UserRole } from '@/types/auth';

// ---------------------------------------------------------------------------
// Local types (for nested company sub-resources)
// ---------------------------------------------------------------------------

export interface SubBrand {
  id: string;
  name: string;
  slug: string;
  isDefault: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CompanyUser {
  id: string;
  companyId: string;
  subBrandId: string | null;
  email: string;
  fullName: string;
  role: UserRole;
  registrationMethod: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface OrgCode {
  id: string;
  companyId: string;
  code: string;
  isActive: boolean;
  createdBy: string;
  createdAt: string;
}

// ---------------------------------------------------------------------------
// Company core
// ---------------------------------------------------------------------------

export function useCompany(id: string) {
  return useQuery({
    queryKey: ['platform-company', id],
    queryFn: async () => {
      const res = await api.get<Company>(`/api/v1/platform/companies/${id}`);
      return res.data;
    },
  });
}

export function useUpdateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Company> }) => {
      const res = await api.patch<Company>(`/api/v1/platform/companies/${id}`, data);
      return res.data;
    },
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['platform-company', id] });
      queryClient.invalidateQueries({ queryKey: ['platform-companies'] });
    },
  });
}

export function useDeactivateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/platform/companies/${id}/deactivate`);
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['platform-company', id] });
      queryClient.invalidateQueries({ queryKey: ['platform-companies'] });
    },
  });
}

export function useReactivateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/platform/companies/${id}/reactivate`);
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['platform-company', id] });
      queryClient.invalidateQueries({ queryKey: ['platform-companies'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Company sub-resources (nested endpoints)
// ---------------------------------------------------------------------------

export function useCompanySubBrands(companyId: string) {
  return useQuery({
    queryKey: ['platform-company-sub-brands', companyId],
    queryFn: async () => {
      const res = await api.get<SubBrand[]>(
        `/api/v1/platform/companies/${companyId}/sub_brands/`,
        { page: '1', per_page: '100' },
      );
      return { data: res.data, total: (res.meta as { total?: number }).total ?? res.data.length };
    },
  });
}

export function useCompanyUsers(companyId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['platform-company-users', companyId],
    queryFn: async () => {
      const res = await api.get<CompanyUser[]>(
        `/api/v1/platform/companies/${companyId}/users/`,
        { page: '1', per_page: '5' },
      );
      return { data: res.data, total: (res.meta as { total?: number }).total ?? 0 };
    },
    enabled,
  });
}

export function useCompanyOrgCode(companyId: string) {
  return useQuery({
    queryKey: ['platform-company-org-code', companyId],
    queryFn: async () => {
      const res = await api.get<OrgCode | null>(
        `/api/v1/platform/companies/${companyId}/org_code/`,
      );
      return res.data;
    },
  });
}

// ---------------------------------------------------------------------------
// Existing platform endpoints with ?company_id= filter
// ---------------------------------------------------------------------------

export function useCompanyCatalogs(companyId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['platform-company-catalogs', companyId],
    queryFn: async () => {
      const res = await api.get<Catalog[]>(
        '/api/v1/platform/catalogs/',
        { company_id: companyId, page: '1', per_page: '5' },
      );
      return { data: res.data, total: (res.meta as { total?: number }).total ?? 0 };
    },
    enabled,
  });
}

export function useCompanyOrders(companyId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['platform-company-orders', companyId],
    queryFn: async () => {
      const res = await api.get<Order[]>(
        '/api/v1/platform/orders/',
        { company_id: companyId, page: '1', per_page: '5' },
      );
      return { data: res.data, total: (res.meta as { total?: number }).total ?? 0 };
    },
    enabled,
  });
}

export function useCompanyInvoices(companyId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['platform-company-invoices', companyId],
    queryFn: async () => {
      const res = await api.get<InvoiceSummary[]>(
        '/api/v1/platform/invoices/',
        { company_id: companyId, page: '1', per_page: '5' },
      );
      return { data: res.data, total: (res.meta as { total?: number }).total ?? 0 };
    },
    enabled,
  });
}

// ---------------------------------------------------------------------------
// Summary counts (lightweight — per_page=1, only reads meta.total)
// ---------------------------------------------------------------------------

export function useCompanyCounts(companyId: string) {
  const endpoints = [
    { key: 'subBrands', url: `/api/v1/platform/companies/${companyId}/sub_brands/` },
    { key: 'users', url: `/api/v1/platform/companies/${companyId}/users/` },
    { key: 'catalogs', url: '/api/v1/platform/catalogs/', params: { company_id: companyId } },
    { key: 'orders', url: '/api/v1/platform/orders/', params: { company_id: companyId } },
    { key: 'invoices', url: '/api/v1/platform/invoices/', params: { company_id: companyId } },
  ];

  return useQuery({
    queryKey: ['platform-company-counts', companyId],
    queryFn: async () => {
      const results = await Promise.all(
        endpoints.map(async (ep) => {
          const params = { page: '1', per_page: '1', ...(ep.params ?? {}) };
          const res = await api.get<unknown[]>(ep.url, params);
          return { key: ep.key, total: (res.meta as { total?: number }).total ?? 0 };
        }),
      );
      return Object.fromEntries(results.map((r) => [r.key, r.total])) as Record<string, number>;
    },
  });
}
