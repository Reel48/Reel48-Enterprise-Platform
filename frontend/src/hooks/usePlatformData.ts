import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type { Company } from '@/types/companies';

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
