'use client';

import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';

interface CompanyOverview {
  activeUsers: number;
}

export function useCompanyOverview() {
  return useQuery({
    queryKey: ['analytics', 'company-overview'],
    queryFn: async () => {
      const res = await api.get<CompanyOverview>('/api/v1/analytics/overview');
      return res.data;
    },
  });
}
