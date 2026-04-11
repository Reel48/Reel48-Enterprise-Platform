'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import {
  Button,
  InlineNotification,
  Link,
  TextInput,
} from '@carbon/react';

import { useAuth } from '@/lib/auth/hooks';

export default function LoginPage() {
  const { signIn } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await signIn(email, password);
      router.replace('/dashboard');
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : 'Unable to sign in. Please check your credentials.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-sm">
      <div className="mb-8 text-center">
        <Image
          src="/reel48-logo-black.svg"
          alt="Reel48+"
          width={140}
          height={35}
          priority
          className="mx-auto mb-4"
        />
        <p className="text-text-secondary">
          Sign in to your account
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        {error && (
          <InlineNotification
            kind="error"
            title="Sign in failed"
            subtitle={error}
            onCloseButtonClick={() => setError(null)}
            lowContrast
          />
        )}

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
          id="password"
          labelText="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />

        <Button
          kind="primary"
          type="submit"
          disabled={isSubmitting}
          className="w-full"
        >
          {isSubmitting ? 'Signing in...' : 'Sign in'}
        </Button>
      </form>

      <div className="mt-6 flex flex-col gap-2 text-center text-sm">
        <Link href="/register">
          Don&apos;t have an account? Register with an org code
        </Link>
        <Link href="/invite">Have an invite? Register here</Link>
      </div>
    </div>
  );
}
