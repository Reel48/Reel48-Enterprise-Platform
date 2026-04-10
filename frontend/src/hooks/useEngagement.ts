'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type {
  NotificationListMeta,
  NotificationSummary,
  WishlistItem,
} from '@/types/engagement';
import type { PaginationMeta } from '@/types/api';

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Wishlists
// ---------------------------------------------------------------------------

interface WishlistListResult {
  data: WishlistItem[];
  meta: PaginationMeta;
}

export function useWishlist(params?: { page?: number; perPage?: number }) {
  return useQuery({
    queryKey: ['wishlist', params],
    queryFn: async (): Promise<WishlistListResult> => {
      const qp: Record<string, string> = {};
      if (params?.page) qp.page = String(params.page);
      if (params?.perPage) qp.per_page = String(params.perPage);

      const res = await api.get<WishlistItem[]>('/api/v1/wishlists/', qp);
      return {
        data: res.data,
        meta: res.meta as unknown as PaginationMeta,
      };
    },
  });
}

export function useAddToWishlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      productId: string;
      catalogId?: string;
      notes?: string;
    }) => {
      const res = await api.post<WishlistItem>('/api/v1/wishlists/', body);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wishlist'] });
      queryClient.invalidateQueries({ queryKey: ['wishlist-check'] });
    },
  });
}

export function useRemoveFromWishlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (wishlistId: string) => {
      await api.delete<void>(`/api/v1/wishlists/${wishlistId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wishlist'] });
      queryClient.invalidateQueries({ queryKey: ['wishlist-check'] });
    },
  });
}

export function useCheckWishlist(productIds: string[]) {
  return useQuery({
    queryKey: ['wishlist-check', productIds],
    queryFn: async () => {
      if (productIds.length === 0) return {};
      const res = await api.post<Record<string, boolean>>(
        '/api/v1/wishlists/check',
        { productIds },
      );
      return res.data;
    },
    enabled: productIds.length > 0,
  });
}
