'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  SideNav,
  SideNavItems,
  SideNavLink,
  Theme,
} from '@carbon/react';
import {
  Dashboard,
  Catalog,
  ShoppingCart,
  UserProfile,
  GroupResource,
  Task,
  Policy,
  Analytics,
  Receipt,
  Enterprise,
  Settings,
  Store,
  Notification,
  FavoriteFilled,
  Product,
  Idea,
  AiGenerate,
  ArrowsHorizontal,
} from '@carbon/react/icons';
import { useQuery } from '@tanstack/react-query';

import type { CarbonIconType } from '@carbon/icons-react/lib/CarbonIcon';

import type { UserRole } from '@/types/auth';
import type { Profile } from '@/types/profiles';
import { useAuth } from '@/lib/auth/hooks';
import { api } from '@/lib/api/client';
import { S3Image } from '@/components/ui/S3Image';

interface NavItem {
  label: string;
  href: string;
  icon: CarbonIconType;
}

const employeeNav: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: Dashboard },
  { label: 'Catalog', href: '/catalog', icon: Catalog },
  { label: 'Orders', href: '/orders', icon: ShoppingCart },
  { label: 'Wishlist', href: '/wishlist', icon: FavoriteFilled },
  { label: 'Notifications', href: '/notifications', icon: Notification },
  { label: 'Profile', href: '/profile', icon: UserProfile },
];

const regionalManagerNav: NavItem[] = [
  ...employeeNav,
  { label: 'Bulk Orders', href: '/bulk-orders', icon: GroupResource },
  { label: 'Approvals', href: '/admin/approvals', icon: Task },
  { label: 'Invoices', href: '/invoices', icon: Receipt },
];

const subBrandAdminNav: NavItem[] = [
  ...regionalManagerNav,
  { label: 'Manage Products', href: '/catalog/manage', icon: Catalog },
  { label: 'Manage Catalogs', href: '/catalog/manage/catalogs', icon: Store },
  { label: 'Users', href: '/admin/users', icon: UserProfile },
  { label: 'Analytics', href: '/admin/analytics', icon: Analytics },
  { label: 'Brand Settings', href: '/settings', icon: Settings },
];

const corporateAdminNav: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: Dashboard },
  { label: 'Orders', href: '/orders', icon: ShoppingCart },
  { label: 'Catalogs', href: '/catalog', icon: Catalog },
  { label: 'Wishlist', href: '/wishlist', icon: FavoriteFilled },
  { label: 'Invoices', href: '/invoices', icon: Receipt },
  { label: 'Notifications', href: '/notifications', icon: Notification },
  { label: 'Users', href: '/admin/users', icon: UserProfile },
  { label: 'Approvals', href: '/admin/approvals', icon: Task },
  { label: 'Brand Settings', href: '/settings', icon: Settings },
  { label: 'Analytics', href: '/admin/analytics', icon: Analytics },
  { label: 'Products', href: '/products', icon: Product },
  { label: 'InsideReel48+', href: '/inside', icon: Idea },
  { label: 'Reel48+ AI', href: '/ai', icon: AiGenerate },
];

const platformAdminNav: NavItem[] = [
  { label: 'Platform Dashboard', href: '/platform/dashboard', icon: Dashboard },
  { label: 'Companies', href: '/platform/companies', icon: Enterprise },
  { label: 'Catalogs', href: '/platform/catalogs', icon: Catalog },
  { label: 'Invoices', href: '/platform/invoices', icon: Receipt },
  { label: 'Analytics', href: '/platform/analytics', icon: Analytics },
];

const navByRole: Record<UserRole, NavItem[]> = {
  employee: employeeNav,
  regional_manager: regionalManagerNav,
  sub_brand_admin: subBrandAdminNav,
  corporate_admin: corporateAdminNav,
  reel48_admin: platformAdminNav,
};

function ProfileInitial({ name }: { name: string }) {
  const initial = name.charAt(0).toUpperCase();
  return (
    <div
      className="flex items-center justify-center rounded-full text-xs font-semibold"
      style={{
        width: 32,
        height: 32,
        backgroundColor: 'var(--r48-teal-700)',
        color: '#ffffff',
      }}
    >
      {initial}
    </div>
  );
}

function formatRoleLabel(role: string): string {
  return role
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

  const role = user?.tenantContext.role ?? 'employee';
  const navItems = navByRole[role];
  const companyName = user?.companyName || '';
  const showProfileSection = role === 'corporate_admin';

  const { data: profile } = useQuery({
    queryKey: ['my-profile'],
    queryFn: async () => {
      const res = await api.get<Profile>('/api/v1/profiles/me');
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
    enabled: !!user && showProfileSection,
  });

  const profilePhotoS3Key = profile?.profilePhotoUrl ?? null;

  return (
    <Theme theme="g10">
      <SideNav
        aria-label="Side navigation"
        isFixedNav
        expanded
        isChildOfHeader={false}
        style={{
          backgroundColor: '#ffffff',
          borderRight: '1px solid var(--cds-border-subtle-01)',
          top: 0,
          height: '100vh',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {/* Company name header area */}
          <div
            className="flex items-center px-4"
            style={{
              height: '48px',
              borderBottom: '1px solid var(--cds-border-subtle-01)',
              flexShrink: 0,
            }}
          >
            <span
              className="text-sm font-semibold truncate"
              style={{ color: 'var(--cds-text-primary)' }}
              title={companyName}
            >
              {companyName}
            </span>
          </div>

          {/* Scrollable nav items */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <SideNavItems className="pt-2">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <SideNavLink
                    key={item.href}
                    href={item.href}
                    renderIcon={() => (
                      <Icon
                        size={20}
                        style={
                          isActive
                            ? { fill: 'var(--r48-teal-700)' }
                            : { fill: 'var(--cds-icon-secondary)' }
                        }
                      />
                    )}
                    isActive={isActive}
                    style={
                      isActive
                        ? {
                            color: 'var(--r48-teal-700)',
                            borderLeft: '3px solid var(--r48-teal-700)',
                            backgroundColor: 'var(--r48-teal-50)',
                          }
                        : { color: 'var(--cds-text-secondary)' }
                    }
                  >
                    {item.label}
                  </SideNavLink>
                );
              })}
            </SideNavItems>
          </div>

          {/* Bottom profile section */}
          {showProfileSection && user && (
            <div
              className="flex items-center gap-3 px-4 py-3"
              style={{
                borderTop: '1px solid var(--cds-border-subtle-01)',
                flexShrink: 0,
              }}
            >
              {/* Profile photo or initial */}
              <div className="flex-shrink-0 rounded-full overflow-hidden">
                {profilePhotoS3Key ? (
                  <S3Image
                    s3Key={profilePhotoS3Key}
                    alt="Profile"
                    width={32}
                    height={32}
                    className="rounded-full object-cover"
                    fallback={<ProfileInitial name={user.fullName} />}
                  />
                ) : (
                  <ProfileInitial name={user.fullName} />
                )}
              </div>

              {/* Name and role */}
              <div className="flex-1 min-w-0">
                <p
                  className="text-sm font-medium truncate"
                  style={{ color: 'var(--cds-text-primary)' }}
                >
                  {user.fullName}
                </p>
                <p
                  className="text-xs truncate"
                  style={{ color: 'var(--cds-text-secondary)' }}
                >
                  {formatRoleLabel(role)}
                </p>
              </div>

              {/* Arrow link to profile page */}
              <Link
                href="/profile"
                className="flex-shrink-0 flex items-center justify-center rounded"
                style={{ width: 32, height: 32 }}
                aria-label="Go to profile"
              >
                <ArrowsHorizontal
                  size={16}
                  style={{ fill: 'var(--cds-icon-secondary)' }}
                />
              </Link>
            </div>
          )}
        </div>
      </SideNav>
    </Theme>
  );
}
