'use client';

import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type { PlatformOverview } from '@/types/analytics';

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
