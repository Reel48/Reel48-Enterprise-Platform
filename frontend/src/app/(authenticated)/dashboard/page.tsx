'use client';

import Image from 'next/image';
import Link from 'next/link';
import {
  ActionableNotification,
  Button,
  ProgressBar,
  Tag,
  Tile,
  ClickableTile,
} from '@carbon/react';
import {
  ShoppingCart,
  Catalog,
  FavoriteFilled,
  Notification as NotificationIcon,
  UserProfile,
  GroupResource,
  Task,
  ArrowRight,
} from '@carbon/react/icons';
import { useQuery } from '@tanstack/react-query';

import { useAuth } from '@/lib/auth/hooks';
import { api } from '@/lib/api/client';
import {
  useNotifications,
  useUnreadNotificationCount,
  useWishlist,
} from '@/hooks/useEngagement';
import type { NotificationSummary } from '@/types/engagement';
import type { UserRole } from '@/types/auth';

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(price);
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

function statusColor(status: string): 'teal' | 'blue' | 'purple' | 'gray' | 'green' | 'red' {
  switch (status) {
    case 'delivered':
      return 'green';
    case 'shipped':
    case 'processing':
      return 'blue';
    case 'approved':
      return 'teal';
    case 'pending':
      return 'purple';
    case 'cancelled':
      return 'red';
    default:
      return 'gray';
  }
}

// ---------------------------------------------------------------------------
// Data hooks for dashboard
// ---------------------------------------------------------------------------

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

interface OrderSummary {
  id: string;
  orderNumber: string;
  status: string;
  totalAmount: number;
  createdAt: string;
}

function useMyOrders(perPage = 5) {
  return useQuery({
    queryKey: ['my-orders', perPage],
    queryFn: async () => {
      const res = await api.get<OrderSummary[]>('/api/v1/orders/my/', {
        page: '1',
        per_page: String(perPage),
      });
      return {
        data: res.data,
        total: (res.meta as { total?: number })?.total ?? 0,
      };
    },
  });
}

interface CatalogSummary {
  id: string;
  name: string;
  status: string;
}

function useActiveCatalogs() {
  return useQuery({
    queryKey: ['active-catalogs-count'],
    queryFn: async () => {
      const res = await api.get<CatalogSummary[]>('/api/v1/catalogs/', {
        status: 'active',
        page: '1',
        per_page: '1',
      });
      return (res.meta as { total?: number })?.total ?? 0;
    },
  });
}

// ---------------------------------------------------------------------------
// Profile completeness
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// KPI Card
// ---------------------------------------------------------------------------

function KPICard({
  label,
  value,
  icon: Icon,
  href,
}: {
  label: string;
  value: number | string;
  icon: typeof ShoppingCart;
  href: string;
}) {
  return (
    <ClickableTile href={href} className="flex items-center gap-4">
      <div className="flex items-center justify-center w-10 h-10 rounded-full bg-teal-50 text-interactive">
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-semibold text-text-primary">{value}</p>
        <p className="text-xs text-text-secondary">{label}</p>
      </div>
    </ClickableTile>
  );
}

// ---------------------------------------------------------------------------
// Employee Dashboard
// ---------------------------------------------------------------------------

function EmployeeDashboard({ fullName }: { fullName: string }) {
  const { data: profile } = useMyProfile();
  const { data: ordersData } = useMyOrders(5);
  const { data: notifData } = useNotifications({ page: 1, perPage: 5, unreadOnly: true });
  const { data: wishlistData } = useWishlist({ page: 1, perPage: 6 });
  const activeCatalogCount = useActiveCatalogs();
  const unreadCount = useUnreadNotificationCount();

  const profileCompleteness = calculateProfileCompleteness(profile);
  const orders = ordersData?.data ?? [];
  const orderTotal = ordersData?.total ?? 0;
  const notifications = notifData?.data ?? [];
  const wishlistItems = wishlistData?.data ?? [];
  const wishlistTotal = wishlistData?.meta?.total ?? 0;

  return (
    <div className="flex flex-col gap-6">
      {/* Onboarding Banner */}
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

      {/* Row 1: Welcome + Profile Completeness */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Tile>
          <h1 className="text-2xl font-semibold text-text-primary mb-1">
            Welcome back, {fullName}
          </h1>
          <p className="text-sm text-text-secondary">
            Here&apos;s what&apos;s happening with your apparel program
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

      {/* Row 2: KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          label="My Orders"
          value={orderTotal}
          icon={ShoppingCart}
          href="/orders"
        />
        <KPICard
          label="Active Catalogs"
          value={activeCatalogCount.data ?? 0}
          icon={Catalog}
          href="/catalog"
        />
        <KPICard
          label="Wishlist Items"
          value={wishlistTotal}
          icon={FavoriteFilled}
          href="/wishlist"
        />
        <KPICard
          label="Unread Notifications"
          value={unreadCount}
          icon={NotificationIcon}
          href="/notifications"
        />
      </div>

      {/* Row 3: Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent Orders */}
        <Tile>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-text-primary">
              Recent Orders
            </h2>
            <Link
              href="/orders"
              className="text-sm text-link-primary flex items-center gap-1"
            >
              View all <ArrowRight size={16} />
            </Link>
          </div>
          {orders.length === 0 ? (
            <p className="text-sm text-text-secondary py-4 text-center">
              No orders yet.{' '}
              <Link href="/catalog" className="text-link-primary">
                Browse catalogs
              </Link>
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {orders.map((order) => (
                <Link
                  key={order.id}
                  href={`/orders/${order.id}`}
                  className="flex items-center justify-between py-2 px-2 rounded hover:bg-layer-hover-01 transition-colors"
                >
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      {order.orderNumber}
                    </p>
                    <p className="text-xs text-text-secondary">
                      {formatDate(order.createdAt)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">
                      {formatPrice(order.totalAmount)}
                    </span>
                    <Tag type={statusColor(order.status)} size="sm">
                      {order.status}
                    </Tag>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Tile>

        {/* Unread Notifications */}
        <Tile>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-text-primary">
              Unread Notifications
            </h2>
            <Link
              href="/notifications"
              className="text-sm text-link-primary flex items-center gap-1"
            >
              View all <ArrowRight size={16} />
            </Link>
          </div>
          {notifications.length === 0 ? (
            <p className="text-sm text-text-secondary py-4 text-center">
              All caught up!
            </p>
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

      {/* Row 4: Wishlist Highlights */}
      <Tile>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-text-primary">
            Wishlist Highlights
          </h2>
          {wishlistTotal > 0 && (
            <Link
              href="/wishlist"
              className="text-sm text-link-primary flex items-center gap-1"
            >
              View full wishlist <ArrowRight size={16} />
            </Link>
          )}
        </div>
        {wishlistItems.length === 0 ? (
          <p className="text-sm text-text-secondary py-4 text-center">
            Browse catalogs to start your wishlist.{' '}
            <Link href="/catalog" className="text-link-primary">
              Explore now
            </Link>
          </p>
        ) : (
          <div className="flex gap-4 overflow-x-auto pb-2">
            {wishlistItems.map((item) => (
              <div
                key={item.id}
                className="flex-shrink-0 w-40"
              >
                {item.productImageUrl ? (
                  <div className="relative w-full h-28 bg-layer-02 rounded mb-2 overflow-hidden">
                    <Image
                      src={item.productImageUrl}
                      alt={item.productName}
                      fill
                      className="object-cover"
                    />
                  </div>
                ) : (
                  <div className="w-full h-28 bg-layer-02 rounded mb-2 flex items-center justify-center">
                    <Catalog size={24} className="text-text-secondary" />
                  </div>
                )}
                <p className="text-xs font-medium text-text-primary truncate">
                  {item.productName}
                </p>
                <p className="text-xs text-interactive">
                  {formatPrice(item.productUnitPrice)}
                </p>
              </div>
            ))}
          </div>
        )}
      </Tile>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Manager/Admin Dashboard (extends Employee)
// ---------------------------------------------------------------------------

function ManagerAdminExtras() {
  // Fetch team-level data for managers/admins
  const { data: allOrders } = useQuery({
    queryKey: ['team-orders-count'],
    queryFn: async () => {
      const res = await api.get<unknown[]>('/api/v1/orders/', {
        page: '1',
        per_page: '1',
      });
      return (res.meta as { total?: number })?.total ?? 0;
    },
  });

  const { data: pendingApprovals } = useQuery({
    queryKey: ['pending-approvals-count'],
    queryFn: async () => {
      const res = await api.get<unknown[]>('/api/v1/approvals/', {
        status: 'pending',
        page: '1',
        per_page: '1',
      });
      return (res.meta as { total?: number })?.total ?? 0;
    },
  });

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <ClickableTile href="/orders" className="flex items-center gap-4">
        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-teal-50 text-interactive">
          <GroupResource size={20} />
        </div>
        <div>
          <p className="text-2xl font-semibold text-text-primary">
            {allOrders ?? 0}
          </p>
          <p className="text-xs text-text-secondary">Team Orders</p>
        </div>
      </ClickableTile>

      <ClickableTile href="/admin/approvals" className="flex items-center gap-4">
        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-teal-50 text-interactive">
          <Task size={20} />
        </div>
        <div>
          <p className="text-2xl font-semibold text-text-primary">
            {pendingApprovals ?? 0}
          </p>
          <p className="text-xs text-text-secondary">Pending Approvals</p>
        </div>
      </ClickableTile>

      <ClickableTile href="/admin/analytics" className="flex items-center gap-4">
        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-teal-50 text-interactive">
          <Catalog size={20} />
        </div>
        <div>
          <p className="text-sm font-medium text-text-primary">
            Analytics
          </p>
          <p className="text-xs text-text-secondary">View detailed reports</p>
        </div>
      </ClickableTile>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Dashboard Page
// ---------------------------------------------------------------------------

const MANAGER_AND_ABOVE: UserRole[] = [
  'reel48_admin',
  'corporate_admin',
  'sub_brand_admin',
  'regional_manager',
];

export default function DashboardPage() {
  const { user } = useAuth();

  if (!user) return null;

  const role = user.tenantContext.role;
  const isManagerOrAbove = MANAGER_AND_ABOVE.includes(role);

  return (
    <div className="flex flex-col gap-6">
      {isManagerOrAbove && (
        <>
          <h2 className="text-base font-semibold text-text-primary">
            Team Overview
          </h2>
          <ManagerAdminExtras />
        </>
      )}
      <EmployeeDashboard fullName={user.fullName} />
    </div>
  );
}
