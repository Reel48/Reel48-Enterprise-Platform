'use client';

import Link from 'next/link';
import {
  ActionableNotification,
  Button,
  ProgressBar,
  Tile,
} from '@carbon/react';
import {
  Notification as NotificationIcon,
  UserProfile,
  Store,
  ArrowRight,
} from '@carbon/react/icons';
import { useQuery } from '@tanstack/react-query';

import { useAuth } from '@/lib/auth/hooks';
import { api } from '@/lib/api/client';
import {
  useNotifications,
  useUnreadNotificationCount,
} from '@/hooks/useEngagement';
import type { NotificationSummary } from '@/types/engagement';
import type { UserRole } from '@/types/auth';

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

interface ProfileData {
  shirtSize: string | null;
  pantSize: string | null;
  shoeSize: string | null;
  deliveryAddressLine1: string | null;
  department: string | null;
  jobTitle: string | null;
  onboardingComplete: boolean;
}

function useMyProfile() {
  return useQuery({
    queryKey: ['my-profile'],
    queryFn: async () => {
      const res = await api.get<ProfileData>('/api/v1/profiles/me');
      return res.data;
    },
  });
}

const PROFILE_FIELDS: (keyof ProfileData)[] = [
  'shirtSize',
  'pantSize',
  'shoeSize',
  'deliveryAddressLine1',
  'department',
  'jobTitle',
];

function calculateProfileCompleteness(profile: ProfileData | undefined): number {
  if (!profile) return 0;
  const filled = PROFILE_FIELDS.filter((f) => profile[f] != null && profile[f] !== '').length;
  return Math.round((filled / PROFILE_FIELDS.length) * 100);
}

const ADMIN_ROLES: UserRole[] = ['reel48_admin', 'company_admin'];

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: profile } = useMyProfile();
  const { data: notifData } = useNotifications({ page: 1, perPage: 5, unreadOnly: true });
  const unreadCount = useUnreadNotificationCount();

  if (!user) return null;

  const profileCompleteness = calculateProfileCompleteness(profile);
  const notifications = notifData?.data ?? [];
  const isAdmin = ADMIN_ROLES.includes(user.tenantContext.role);

  return (
    <div className="flex flex-col gap-6">
      {profile && !profile.onboardingComplete && (
        <ActionableNotification
          kind="info"
          title="Complete Your Profile"
          subtitle="Set up your sizing, delivery address, and department to get the most out of your apparel program."
          actionButtonLabel="Get Started"
          onActionButtonClick={() => {
            window.location.href = '/onboarding';
          }}
          lowContrast
          hideCloseButton
          className="mb-0"
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Tile>
          <h1 className="text-2xl font-semibold text-text-primary mb-1">
            Welcome back, {user.fullName}
          </h1>
          <p className="text-sm text-text-secondary">
            Here&apos;s an overview of your account
          </p>
        </Tile>

        <Tile>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-text-primary">
              Profile Completeness
            </span>
            <span className="text-sm font-semibold text-interactive">
              {profileCompleteness}%
            </span>
          </div>
          <ProgressBar
            value={profileCompleteness}
            max={100}
            label=""
            size="small"
          />
          {profile && !profile.onboardingComplete && (
            <Button
              kind="ghost"
              size="sm"
              href="/profile"
              renderIcon={UserProfile}
              className="mt-2"
            >
              Complete Your Profile
            </Button>
          )}
        </Tile>
      </div>

      {isAdmin && (
        <Tile>
          <div className="flex items-start gap-4">
            <div className="flex items-center justify-center w-10 h-10 rounded-full bg-teal-50 text-interactive shrink-0">
              <Store size={20} />
            </div>
            <div className="flex-1">
              <h2 className="text-base font-semibold text-text-primary mb-1">
                Shopify integration coming soon
              </h2>
              <p className="text-sm text-text-secondary">
                Product catalog, ordering, and checkout will be powered by Shopify in an
                upcoming release. For now, use this dashboard to manage your team and
                account settings.
              </p>
            </div>
          </div>
        </Tile>
      )}

      <Tile>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-text-primary">
            Unread Notifications
            {unreadCount > 0 && (
              <span className="ml-2 text-sm font-normal text-text-secondary">
                ({unreadCount})
              </span>
            )}
          </h2>
          <Link
            href="/notifications"
            className="text-sm text-link-primary flex items-center gap-1"
          >
            View all <ArrowRight size={16} />
          </Link>
        </div>
        {notifications.length === 0 ? (
          <div className="flex items-center gap-2 py-4 justify-center text-text-secondary">
            <NotificationIcon size={16} />
            <span className="text-sm">All caught up!</span>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {notifications.map((n: NotificationSummary) => (
              <div
                key={n.id}
                className="flex items-start gap-2 py-2 px-2 rounded hover:bg-layer-hover-01 transition-colors"
              >
                <span className="w-2 h-2 mt-1.5 rounded-full bg-interactive flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm text-text-primary truncate">
                    {n.title}
                  </p>
                  <p className="text-xs text-text-secondary">
                    {formatDate(n.createdAt)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Tile>
    </div>
  );
}
