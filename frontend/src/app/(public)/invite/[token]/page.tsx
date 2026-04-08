'use client';

import { useState } from 'react';
import {
  Button,
  InlineNotification,
  Link,
  TextInput,
} from '@carbon/react';

import { api, ApiRequestError } from '@/lib/api/client';
import type { RegisterData } from '@/types/registration';

interface InviteRegisterPageProps {
  params: { token: string };
}

export default function InviteRegisterPage({ params }: InviteRegisterPageProps) {
  const { token } = params;

  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const isSuccess = successMessage !== '';

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await api.post<RegisterData>(
        '/api/v1/auth/register-from-invite',
        { token, email, fullName, password },
        { skipAuth: true },
      );

      setSuccessMessage(response.data.message);
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? 'This invite link is invalid or has expired. Please contact your administrator.'
          : 'Something went wrong. Please try again.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-sm">
      <div className="mb-8 text-center">
        <h1 className="mb-2 text-3xl font-semibold text-text-primary">
          Reel48+
        </h1>
        <p className="text-text-secondary">
          {isSuccess ? 'Registration complete' : 'Complete your registration'}
        </p>
      </div>

      {error && (
        <div className="mb-6">
          <InlineNotification
            kind="error"
            title="Error"
            subtitle={error}
            onCloseButtonClick={() => setError(null)}
            lowContrast
          />
        </div>
      )}

      {isSuccess ? (
        <div className="flex flex-col gap-6">
          <InlineNotification
            kind="success"
            title="Success"
            subtitle={successMessage}
            hideCloseButton
            lowContrast
          />
          <Link href="/login" className="text-center">
            Sign in to your account
          </Link>
        </div>
      ) : (
        <form onSubmit={handleRegister} className="flex flex-col gap-6">
          <TextInput
            id="email"
            labelText="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />

          <TextInput
            id="full-name"
            labelText="Full Name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            autoComplete="name"
          />

          <TextInput
            id="password"
            labelText="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            helperText="Must be at least 8 characters"
            autoComplete="new-password"
          />

          <TextInput
            id="confirm-password"
            labelText="Confirm Password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
          />

          <Button
            kind="primary"
            type="submit"
            disabled={isSubmitting}
            className="w-full"
          >
            {isSubmitting ? 'Creating account...' : 'Create Account'}
          </Button>
        </form>
      )}

      {!isSuccess && (
        <div className="mt-6 text-center text-sm">
          <Link href="/login">Already have an account? Sign in</Link>
        </div>
      )}
    </div>
  );
}
