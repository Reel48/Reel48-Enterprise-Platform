'use client';

import { useState } from 'react';
import {
  Button,
  Dropdown,
  InlineNotification,
  Link,
  TextInput,
} from '@carbon/react';

import { api, ApiRequestError } from '@/lib/api/client';
import type { RegisterData, SubBrandSummary, ValidateOrgCodeData } from '@/types/registration';

type RegistrationStep = 'code' | 'details' | 'success';

export default function RegisterPage() {
  const [step, setStep] = useState<RegistrationStep>('code');

  // Step 1 state
  const [code, setCode] = useState('');

  // Validated data from Step 1
  const [companyName, setCompanyName] = useState('');
  const [subBrands, setSubBrands] = useState<SubBrandSummary[]>([]);
  const [selectedSubBrand, setSelectedSubBrand] = useState<SubBrandSummary | null>(null);

  // Step 2 state
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Shared state
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  async function handleValidateCode(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await api.post<ValidateOrgCodeData>(
        '/api/v1/auth/validate-org-code',
        { code },
        { skipAuth: true },
      );

      const data = response.data;
      setCompanyName(data.companyName);
      setSubBrands(data.subBrands);

      const defaultBrand = data.subBrands.find((sb) => sb.isDefault) ?? data.subBrands[0];
      setSelectedSubBrand(defaultBrand ?? null);

      setStep('details');
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? 'Invalid registration code. Please check your code and try again.'
          : 'Something went wrong. Please try again.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (!selectedSubBrand) {
      setError('Please select a location.');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await api.post<RegisterData>(
        '/api/v1/auth/register',
        {
          code,
          subBrandId: selectedSubBrand.id,
          email,
          fullName,
          password,
        },
        { skipAuth: true },
      );

      setSuccessMessage(response.data.message);
      setStep('success');
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? 'Registration failed. Please try again.'
          : 'Something went wrong. Please try again.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleBack() {
    setError(null);
    setStep('code');
  }

  return (
    <div className="w-full max-w-sm">
      <div className="mb-8 text-center">
        <h1 className="mb-2 text-3xl font-semibold text-text-primary">
          Reel48+
        </h1>
        <p className="text-text-secondary">
          {step === 'code' && 'Register with an organization code'}
          {step === 'details' && `Registering with ${companyName}`}
          {step === 'success' && 'Registration complete'}
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

      {step === 'code' && (
        <form onSubmit={handleValidateCode} className="flex flex-col gap-6">
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

          <Button
            kind="primary"
            type="submit"
            disabled={isSubmitting}
            className="w-full"
          >
            {isSubmitting ? 'Validating...' : 'Validate Code'}
          </Button>
        </form>
      )}

      {step === 'details' && (
        <form onSubmit={handleRegister} className="flex flex-col gap-6">
          {subBrands.length > 1 && (
            <Dropdown
              id="sub-brand"
              titleText="Select your location"
              label="Choose a location"
              items={subBrands}
              itemToString={(item: SubBrandSummary | null) => item?.name ?? ''}
              selectedItem={selectedSubBrand}
              onChange={({ selectedItem }: { selectedItem: SubBrandSummary | null }) =>
                setSelectedSubBrand(selectedItem ?? null)
              }
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

          <div className="flex gap-4">
            <Button
              kind="ghost"
              type="button"
              onClick={handleBack}
            >
              Back
            </Button>
            <Button
              kind="primary"
              type="submit"
              disabled={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? 'Creating account...' : 'Create Account'}
            </Button>
          </div>
        </form>
      )}

      {step === 'success' && (
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
      )}

      {step !== 'success' && (
        <div className="mt-6 flex flex-col gap-2 text-center text-sm">
          <Link href="/login">Already have an account? Sign in</Link>
          <Link href="/invite">Have an invite? Register here</Link>
        </div>
      )}
    </div>
  );
}
