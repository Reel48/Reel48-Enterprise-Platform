'use client';

import Image from 'next/image';
import Link from 'next/link';
import {
  HeaderGlobalAction,
  HeaderGlobalBar,
  OverflowMenu,
  OverflowMenuItem,
  Theme,
} from '@carbon/react';
import { ShoppingCart, UserAvatar } from '@carbon/react/icons';

import { useAuth } from '@/lib/auth/hooks';
import { useCartCount } from '@/lib/cart/CartContext';
import { NotificationBell } from '@/components/features/engagement/NotificationBell';

export function Header() {
  const { user, signOut } = useAuth();
  const cartCount = useCartCount();

  const roleLabel = user?.tenantContext.role.replace(/_/g, ' ') ?? '';

  return (
    <Theme theme="g100">
      <header
        className="fixed top-0 flex items-center bg-charcoal-900"
        style={{
          left: '256px',
          right: 0,
          height: '48px',
          zIndex: 8000,
        }}
      >
        <a href="/dashboard" className="flex items-center px-4 h-full">
          <Image
            src="/reel48-logo.svg"
            alt="Reel48+"
            width={86}
            height={23}
            priority
          />
        </a>

        <div className="flex-1" />

        <HeaderGlobalBar>
          {user && (
            <span className="flex items-center gap-2 px-4 text-sm" style={{ color: '#ffffff' }}>
              <span>{user.fullName}</span>
              <span style={{ color: 'rgba(255, 255, 255, 0.7)' }}>({roleLabel})</span>
            </span>
          )}
          {user && user.tenantContext.role !== 'reel48_admin' && (
            <>
              <Link
                href="/orders/new"
                className="relative flex items-center justify-center w-10 h-full"
                aria-label="Cart"
              >
                <ShoppingCart size={20} style={{ color: '#ffffff' }} />
                {cartCount > 0 && (
                  <span
                    className="absolute flex items-center justify-center rounded-full bg-interactive text-xs font-bold"
                    style={{
                      top: '6px',
                      right: '2px',
                      minWidth: '18px',
                      height: '18px',
                      padding: '0 4px',
                      color: '#ffffff',
                      fontSize: '11px',
                    }}
                  >
                    {cartCount > 99 ? '99+' : cartCount}
                  </span>
                )}
              </Link>
              <NotificationBell />
            </>
          )}
          <HeaderGlobalAction
            aria-label="User menu"
            tooltipAlignment="end"
          >
            <OverflowMenu
              renderIcon={UserAvatar}
              flipped
              aria-label="User menu"
            >
              <OverflowMenuItem itemText="Profile" href="/profile" />
              <OverflowMenuItem itemText="Settings" href="/settings" />
              <OverflowMenuItem
                itemText="Sign out"
                onClick={signOut}
                hasDivider
              />
            </OverflowMenu>
          </HeaderGlobalAction>
        </HeaderGlobalBar>
      </header>
    </Theme>
  );
}
