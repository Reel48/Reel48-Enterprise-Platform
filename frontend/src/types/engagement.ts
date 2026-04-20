export type NotificationType =
  | 'announcement'
  | 'buying_window_reminder';

export type NotificationTargetScope = 'company' | 'individual';

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
