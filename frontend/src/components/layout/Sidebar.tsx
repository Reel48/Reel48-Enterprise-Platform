'use client';

import { usePathname } from 'next/navigation';
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
  Analytics,
  Receipt,
  Enterprise,
  Settings,
  Store,
  Notification,
  FavoriteFilled,
} from '@carbon/react/icons';

import type { CarbonIconType } from '@carbon/icons-react/lib/CarbonIcon';

import type { UserRole } from '@/types/auth';
import { useAuth } from '@/lib/auth/hooks';

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
];

const subBrandAdminNav: NavItem[] = [
  ...regionalManagerNav,
  { label: 'Users', href: '/admin/users', icon: UserProfile },
  { label: 'Analytics', href: '/admin/analytics', icon: Analytics },
  { label: 'Brand Settings', href: '/settings', icon: Settings },
];

const corporateAdminNav: NavItem[] = [
  ...subBrandAdminNav,
  { label: 'All Sub-Brands', href: '/admin/brands', icon: Store },
  { label: 'Invoices', href: '/invoices', icon: Receipt },
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

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

  const role = user?.tenantContext.role ?? 'employee';
  const navItems = navByRole[role];

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
          top: '48px',
          height: 'calc(100vh - 48px)',
        }}
      >
        <SideNavItems className="pt-4">
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
      </SideNav>
    </Theme>
  );
}
