'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Button,
  Pagination,
  Tag,
  Toggle,
  Tile,
} from '@carbon/react';
import {
  CheckmarkFilled,
  Catalog,
  ShoppingCart,
  Bullhorn,
  Notification as NotificationIcon,
} from '@carbon/react/icons';

import {
  useNotifications,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
} from '@/hooks/useEngagement';
import type { NotificationSummary } from '@/types/engagement';

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function NotificationTypeIcon({ type }: { type: string }) {
  const size = 20;
  switch (type) {
    case 'catalog_available':
      return <Catalog size={size} />;
    case 'order_update':
      return <ShoppingCart size={size} />;
    case 'announcement':
      return <Bullhorn size={size} />;
    case 'buying_window_reminder':
    default:
      return <NotificationIcon size={size} />;
  }
}

function notificationTypeLabel(type: string): { label: string; color: string } {
  switch (type) {
    case 'catalog_available':
      return { label: 'Catalog', color: 'teal' };
    case 'order_update':
      return { label: 'Order', color: 'blue' };
    case 'buying_window_reminder':
      return { label: 'Reminder', color: 'purple' };
    case 'announcement':
    default:
      return { label: 'Announcement', color: 'gray' };
  }
}

export default function NotificationsPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const { data, isLoading } = useNotifications({
    page,
    perPage,
    unreadOnly,
  });
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const notifications = data?.data ?? [];
  const total = data?.meta?.total ?? 0;
  const unreadCount = data?.meta?.unreadCount ?? 0;

  const handleClick = (n: NotificationSummary) => {
    if (!n.isRead) {
      markRead.mutate(n.id);
    }
    if (n.linkUrl) {
      router.push(n.linkUrl);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">
            Notifications
          </h1>
          {unreadCount > 0 && (
            <p className="text-sm text-text-secondary mt-1">
              {unreadCount} unread
            </p>
          )}
        </div>
        <div className="flex items-center gap-4">
          <Toggle
            id="unread-toggle"
            labelText=""
            labelA="All"
            labelB="Unread"
            toggled={unreadOnly}
            onToggle={(checked: boolean) => {
              setUnreadOnly(checked);
              setPage(1);
            }}
            size="sm"
          />
          {unreadCount > 0 && (
            <Button
              kind="ghost"
              size="sm"
              onClick={() => markAllRead.mutate()}
              renderIcon={CheckmarkFilled}
            >
              Mark all read
            </Button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="py-12 text-center text-text-secondary">
          Loading notifications...
        </div>
      ) : notifications.length === 0 ? (
        <Tile className="py-12 text-center">
          <NotificationIcon size={48} className="mx-auto mb-4 text-text-secondary" />
          <p className="text-lg font-medium text-text-primary">
            {unreadOnly ? 'No unread notifications' : 'No notifications yet'}
          </p>
          <p className="text-sm text-text-secondary mt-1">
            {unreadOnly
              ? 'Switch to "All" to see your notification history'
              : "You'll see updates about orders, catalogs, and announcements here"}
          </p>
        </Tile>
      ) : (
        <div className="flex flex-col gap-2">
          {notifications.map((n) => {
            const tagInfo = notificationTypeLabel(n.notificationType);
            return (
              <Tile
                key={n.id}
                className={`cursor-pointer hover:bg-layer-hover-01 transition-colors ${
                  !n.isRead ? 'border-l-4 border-interactive' : ''
                }`}
                onClick={() => handleClick(n)}
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5 text-text-secondary">
                    <NotificationTypeIcon type={n.notificationType} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Tag
                        type={tagInfo.color as 'teal' | 'blue' | 'purple' | 'gray'}
                        size="sm"
                      >
                        {tagInfo.label}
                      </Tag>
                      <span className="text-xs text-text-secondary">
                        {formatDate(n.createdAt)}
                      </span>
                      {!n.isRead && (
                        <span className="w-2 h-2 rounded-full bg-interactive flex-shrink-0" />
                      )}
                    </div>
                    <p className="text-sm font-medium text-text-primary">
                      {n.title}
                    </p>
                    {n.linkUrl && (
                      <p className="text-xs text-link-primary mt-1">
                        View details
                      </p>
                    )}
                  </div>
                </div>
              </Tile>
            );
          })}
        </div>
      )}

      {total > perPage && (
        <Pagination
          page={page}
          pageSize={perPage}
          pageSizes={[10, 20, 50]}
          totalItems={total}
          onChange={({ page: newPage, pageSize }: { page: number; pageSize: number }) => {
            setPage(newPage);
            setPerPage(pageSize);
          }}
        />
      )}
    </div>
  );
}
