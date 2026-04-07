'use client';

import {
  Header as CarbonHeader,
  HeaderGlobalAction,
  HeaderGlobalBar,
  HeaderName,
  OverflowMenu,
  OverflowMenuItem,
  Theme,
} from '@carbon/react';
import { UserAvatar } from '@carbon/react/icons';

import { useAuth } from '@/lib/auth/hooks';

export function Header() {
  const { user, signOut } = useAuth();

  const roleLabel = user?.tenantContext.role.replace(/_/g, ' ') ?? '';

  return (
    <Theme theme="g100">
      <CarbonHeader
        aria-label="Reel48+"
        className="bg-charcoal-900"
      >
        <HeaderName href="/dashboard" prefix="">
          Reel48+
        </HeaderName>

        <HeaderGlobalBar>
          {user && (
            <span className="flex items-center gap-2 px-4 text-sm text-text-inverse">
              <span>{user.fullName}</span>
              <span className="text-charcoal-500">({roleLabel})</span>
            </span>
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
      </CarbonHeader>
    </Theme>
  );
}
