import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type { Company } from '@/types/companies';
import type { UserRole } from '@/types/auth';

export interface CompanyUser {
  id: string;
  companyId: string;
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

export function useCompanyUsers(companyId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['platform-company-users', companyId],
    queryFn: async () => {
      const res = await api.get<CompanyUser[]>(
        `/api/v1/platform/companies/${companyId}/users/`,
        { page: '1', per_page: '25' },
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
