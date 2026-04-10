'use client';

import { useRef, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Tag } from '@carbon/react';
import { Notification, CheckmarkFilled } from '@carbon/react/icons';

import {
  useNotifications,
  useUnreadNotificationCount,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
} from '@/hooks/useEngagement';
import type { NotificationSummary } from '@/types/engagement';

function formatTimeAgo(dateString: string): string {
  const now = new Date();
  const date = new Date(dateString);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function notificationTypeTag(type: string): { label: string; color: string } {
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

export function NotificationBell() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const unreadCount = useUnreadNotificationCount();
  const { data } = useNotifications({ page: 1, perPage: 5 });
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const notifications = data?.data ?? [];

  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (
      panelRef.current &&
      !panelRef.current.contains(e.target as Node) &&
      buttonRef.current &&
      !buttonRef.current.contains(e.target as Node)
    ) {
      setOpen(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open, handleClickOutside]);

  const handleNotificationClick = (n: NotificationSummary) => {
    if (!n.isRead) {
      markRead.mutate(n.id);
    }
    if (n.linkUrl) {
      router.push(n.linkUrl);
      setOpen(false);
    }
  };

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center justify-center w-10 h-10 text-text-inverse hover:bg-charcoal-800 rounded transition-colors"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
      >
        <Notification size={20} />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] rounded-full bg-support-error text-white text-xs font-semibold px-1">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          ref={panelRef}
          className="absolute right-0 top-12 w-[360px] bg-layer-01 border border-border-subtle-01 shadow-lg rounded z-50"
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle-01">
            <span className="text-sm font-semibold text-text-primary">
              Notifications
            </span>
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

          <div className="max-h-[320px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-text-secondary">
                No notifications yet
              </div>
            ) : (
              notifications.map((n) => {
                const tagInfo = notificationTypeTag(n.notificationType);
                return (
                  <button
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`w-full text-left px-4 py-3 border-b border-border-subtle-01 hover:bg-layer-hover-01 transition-colors ${
                      !n.isRead ? 'bg-teal-50' : ''
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {!n.isRead && (
                        <span className="mt-1.5 w-2 h-2 rounded-full bg-interactive flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Tag type={tagInfo.color as 'teal' | 'blue' | 'purple' | 'gray'} size="sm">
                            {tagInfo.label}
                          </Tag>
                          <span className="text-xs text-text-secondary">
                            {formatTimeAgo(n.createdAt)}
                          </span>
                        </div>
                        <p className="text-sm text-text-primary truncate">
                          {n.title}
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="px-4 py-2 border-t border-border-subtle-01">
            <Button
              kind="ghost"
              size="sm"
              className="w-full"
              onClick={() => {
                router.push('/notifications');
                setOpen(false);
              }}
            >
              View all notifications
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
