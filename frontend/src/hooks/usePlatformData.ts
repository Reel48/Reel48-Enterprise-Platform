import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type { Company } from '@/types/companies';

export interface SubBrand {
  id: string;
  name: string;
  slug: string;
  isDefault: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

/**
 * Fetches all companies for platform admin use (searchable ComboBox).
 */
export function usePlatformCompanies() {
  return useQuery({
    queryKey: ['platform-companies'],
    queryFn: async () => {
      const res = await api.get<Company[]>('/api/v1/platform/companies/', {
        per_page: '100',
      });
      return res.data;
    },
  });
}

/**
 * Fetches sub-brands for a specific company. Only enabled when companyId is set.
 */
export function usePlatformCompanySubBrands(companyId: string | null) {
  return useQuery({
    queryKey: ['platform-company-sub-brands', companyId],
    queryFn: async () => {
      const res = await api.get<SubBrand[]>(
        `/api/v1/platform/companies/${companyId}/sub_brands/`,
      );
      return res.data;
    },
    enabled: !!companyId,
  });
}
