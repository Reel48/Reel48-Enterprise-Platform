'use client';

import { useState } from 'react';
import {
  Button,
  InlineNotification,
  TextInput,
  Tile,
  ToastNotification,
} from '@carbon/react';
import { Password, Save } from '@carbon/react/icons';

import { useAuth } from '@/lib/auth/hooks';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      setToast({ kind: 'error', message: 'New passwords do not match' });
      setTimeout(() => setToast(null), 3000);
      return;
    }

    if (newPassword.length < 8) {
      setToast({ kind: 'error', message: 'Password must be at least 8 characters' });
      setTimeout(() => setToast(null), 3000);
      return;
    }

    setIsChangingPassword(true);
    try {
      const { updatePassword } = await import('aws-amplify/auth');
      await updatePassword({ oldPassword: currentPassword, newPassword });
      setToast({ kind: 'success', message: 'Password changed successfully' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch {
      setToast({ kind: 'error', message: 'Failed to change password. Check your current password.' });
    } finally {
      setIsChangingPassword(false);
      setTimeout(() => setToast(null), 3000);
    }
  };

  if (!user) return null;

  const role = user.tenantContext.role.replace(/_/g, ' ');

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-text-primary">
        Settings
      </h1>

      {/* Account Info */}
      <Tile>
        <h2 className="text-base font-semibold text-text-primary mb-4">
          Account Information
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-text-secondary mb-1">Email</p>
            <p className="text-sm text-text-primary">{user.email}</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary mb-1">Name</p>
            <p className="text-sm text-text-primary">{user.fullName}</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary mb-1">Role</p>
            <p className="text-sm text-text-primary capitalize">{role}</p>
          </div>
          {user.tenantContext.companyId && (
            <div>
              <p className="text-xs text-text-secondary mb-1">Company ID</p>
              <p className="text-sm text-text-primary font-mono">
                {user.tenantContext.companyId}
              </p>
            </div>
          )}
          {user.tenantContext.subBrandId && (
            <div>
              <p className="text-xs text-text-secondary mb-1">Sub-Brand ID</p>
              <p className="text-sm text-text-primary font-mono">
                {user.tenantContext.subBrandId}
              </p>
            </div>
          )}
        </div>
      </Tile>

      {/* Change Password */}
      <Tile>
        <h2 className="text-base font-semibold text-text-primary mb-4">
          Change Password
        </h2>
        <form onSubmit={handleChangePassword} className="flex flex-col gap-4 max-w-md">
          <TextInput
            id="current-password"
            labelText="Current Password"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
          <TextInput
            id="new-password"
            labelText="New Password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            helperText="Must be at least 8 characters"
            autoComplete="new-password"
          />
          <TextInput
            id="confirm-new-password"
            labelText="Confirm New Password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
          <div>
            <Button
              kind="primary"
              type="submit"
              size="sm"
              renderIcon={Password}
              disabled={isChangingPassword || !currentPassword || !newPassword || !confirmPassword}
            >
              {isChangingPassword ? 'Changing...' : 'Change Password'}
            </Button>
          </div>
        </form>
      </Tile>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50">
          <ToastNotification
            kind={toast.kind}
            title={toast.message}
            timeout={3000}
            onCloseButtonClick={() => setToast(null)}
            onClose={() => setToast(null)}
          />
        </div>
      )}
    </div>
  );
}
