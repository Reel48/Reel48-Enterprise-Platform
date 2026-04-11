'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRef, useState, useEffect, useCallback } from 'react';
import { Theme } from '@carbon/react';
import { ShoppingCart, UserAvatar, Logout, UserProfile, Settings } from '@carbon/react/icons';

import { useAuth } from '@/lib/auth/hooks';
import { useCartCount } from '@/lib/cart/CartContext';
import { NotificationBell } from '@/components/features/engagement/NotificationBell';

export function Header() {
  const { user, signOut } = useAuth();
  const cartCount = useCartCount();
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const profileBtnRef = useRef<HTMLButtonElement>(null);

  const roleLabel = user?.tenantContext.role.replace(/_/g, ' ') ?? '';

  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (
      profileRef.current &&
      !profileRef.current.contains(e.target as Node) &&
      profileBtnRef.current &&
      !profileBtnRef.current.contains(e.target as Node)
    ) {
      setProfileOpen(false);
    }
  }, []);

  useEffect(() => {
    if (profileOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [profileOpen, handleClickOutside]);

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

        <div className="flex items-center h-full">
          {user && (
            <span className="flex items-center gap-2 px-4 text-sm text-white">
              <span>{user.fullName}</span>
              <span className="text-white/70">({roleLabel})</span>
            </span>
          )}
          {user && user.tenantContext.role !== 'reel48_admin' && (
            <>
              <Link
                href="/orders/new"
                className="relative flex items-center justify-center w-10 h-full hover:bg-charcoal-800 transition-colors"
                aria-label="Cart"
              >
                <ShoppingCart size={20} className="fill-white" />
                {cartCount > 0 && (
                  <span
                    className="absolute flex items-center justify-center rounded-full bg-interactive text-white text-xs font-bold"
                    style={{
                      top: '6px',
                      right: '2px',
                      minWidth: '18px',
                      height: '18px',
                      padding: '0 4px',
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
          <div className="relative">
            <button
              ref={profileBtnRef}
              onClick={() => setProfileOpen((prev) => !prev)}
              className="flex items-center justify-center w-10 h-full hover:bg-charcoal-800 transition-colors"
              aria-label="User menu"
            >
              <UserAvatar size={20} className="fill-white" />
            </button>
            {profileOpen && (
              <div
                ref={profileRef}
                className="absolute right-0 top-12 w-48 bg-charcoal-900 border border-charcoal-700 rounded shadow-lg z-50 overflow-hidden"
              >
                <a
                  href="/profile"
                  className="flex items-center gap-3 px-4 py-3 text-sm text-white hover:bg-charcoal-800 transition-colors"
                  onClick={() => setProfileOpen(false)}
                >
                  <UserProfile size={16} className="fill-white" />
                  Profile
                </a>
                <a
                  href="/settings"
                  className="flex items-center gap-3 px-4 py-3 text-sm text-white hover:bg-charcoal-800 transition-colors"
                  onClick={() => setProfileOpen(false)}
                >
                  <Settings size={16} className="fill-white" />
                  Settings
                </a>
                <div className="border-t border-charcoal-700" />
                <button
                  onClick={() => { setProfileOpen(false); signOut(); }}
                  className="flex items-center gap-3 w-full px-4 py-3 text-sm text-white hover:bg-charcoal-800 transition-colors"
                >
                  <Logout size={16} className="fill-white" />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>
    </Theme>
  );
}
