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

export default function RegisterPage() {
  const [code, setCode] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

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
        '/api/v1/auth/register',
        { code, email, fullName, password },
        { skipAuth: true },
      );

      setSuccessMessage(response.data.message);
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? 'Registration failed. Please check your details and try again.'
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
          {successMessage ? 'Registration complete' : 'Register with an organization code'}
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

      {successMessage ? (
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
        <>
          <form onSubmit={handleRegister} className="flex flex-col gap-6">
            <TextInput
              id="org-code"
              labelText="Organization Code"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              required
              maxLength={8}
              placeholder="e.g. REEL7K3M"
              autoComplete="off"
            />

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

          <div className="mt-6 flex flex-col gap-2 text-center text-sm">
            <Link href="/login">Already have an account? Sign in</Link>
            <Link href="/invite">Have an invite? Register here</Link>
          </div>
        </>
      )}
    </div>
  );
}
