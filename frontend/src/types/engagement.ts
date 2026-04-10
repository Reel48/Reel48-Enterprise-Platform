export type NotificationType =
  | 'announcement'
  | 'catalog_available'
  | 'buying_window_reminder'
  | 'order_update';

export type NotificationTargetScope = 'company' | 'sub_brand' | 'individual';

export interface NotificationSummary {
  id: string;
  title: string;
  notificationType: NotificationType;
  targetScope: NotificationTargetScope;
  isActive: boolean;
  isRead: boolean;
  linkUrl: string | null;
  createdAt: string;
}

export interface NotificationListMeta {
  page: number;
  perPage: number;
  total: number;
  unreadCount: number;
}

export interface NotificationListResponse {
  data: NotificationSummary[];
  meta: NotificationListMeta;
  errors: unknown[];
}

export interface WishlistItem {
  id: string;
  productId: string;
  catalogId: string | null;
  productName: string;
  productSku: string;
  productUnitPrice: number;
  productImageUrl: string | null;
  productStatus: string;
  isPurchasable: boolean;
  notes: string | null;
  createdAt: string;
}
