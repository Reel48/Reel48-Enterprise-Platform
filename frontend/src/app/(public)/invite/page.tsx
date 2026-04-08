'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Button,
  Link,
  TextInput,
} from '@carbon/react';

export default function InviteLandingPage() {
  const router = useRouter();
  const [token, setToken] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (token.trim()) {
      router.push(`/invite/${encodeURIComponent(token.trim())}`);
    }
  }

  return (
    <div className="w-full max-w-sm">
      <div className="mb-8 text-center">
        <h1 className="mb-2 text-3xl font-semibold text-text-primary">
          Reel48+
        </h1>
        <p className="text-text-secondary">
          Enter your invite token to register
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <TextInput
          id="invite-token"
          labelText="Invite Token"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          required
          placeholder="Paste your invite token"
          autoComplete="off"
        />

        <Button
          kind="primary"
          type="submit"
          className="w-full"
        >
          Continue
        </Button>
      </form>

      <div className="mt-6 flex flex-col gap-2 text-center text-sm">
        <Link href="/login">Already have an account? Sign in</Link>
        <Link href="/register">
          Don&apos;t have an invite? Register with an org code
        </Link>
      </div>
    </div>
  );
}
