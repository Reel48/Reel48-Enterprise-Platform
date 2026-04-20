'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type {
  NotificationListMeta,
  NotificationSummary,
} from '@/types/engagement';

interface NotificationListResult {
  data: NotificationSummary[];
  meta: NotificationListMeta;
}

export function useNotifications(params?: {
  unreadOnly?: boolean;
  page?: number;
  perPage?: number;
}) {
  return useQuery({
    queryKey: ['notifications', params],
    queryFn: async (): Promise<NotificationListResult> => {
      const qp: Record<string, string> = {};
      if (params?.unreadOnly) qp.unread_only = 'true';
      if (params?.page) qp.page = String(params.page);
      if (params?.perPage) qp.per_page = String(params.perPage);

      const res = await api.get<NotificationSummary[]>(
        '/api/v1/notifications/',
        qp,
      );
      return {
        data: res.data,
        meta: res.meta as unknown as NotificationListMeta,
      };
    },
  });
}

export function useUnreadNotificationCount() {
  const { data } = useNotifications({ unreadOnly: false, page: 1, perPage: 1 });
  return data?.meta?.unreadCount ?? 0;
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: string) => {
      const res = await api.post<unknown>(
        `/api/v1/notifications/${notificationId}/read`,
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await api.post<{ markedCount: number }>(
        '/api/v1/notifications/read-all',
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}
