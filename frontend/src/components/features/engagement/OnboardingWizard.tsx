'use client';

import { useState, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  Button,
  Dropdown,
  TextInput,
  ProgressIndicator,
  ProgressStep,
  Tile,
  InlineLoading,
} from '@carbon/react';
import { ArrowRight, ArrowLeft, Checkmark } from '@carbon/react/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ProfileData {
  shirtSize: string | null;
  pantSize: string | null;
  shoeSize: string | null;
  deliveryAddressLine1: string | null;
  deliveryAddressLine2: string | null;
  deliveryCity: string | null;
  deliveryState: string | null;
  deliveryZip: string | null;
  deliveryCountry: string | null;
  department: string | null;
  jobTitle: string | null;
  onboardingComplete: boolean;
}

interface WizardFormData {
  shirtSize: string;
  pantSize: string;
  shoeSize: string;
  deliveryAddressLine1: string;
  deliveryAddressLine2: string;
  deliveryCity: string;
  deliveryState: string;
  deliveryZip: string;
  deliveryCountry: string;
  department: string;
  jobTitle: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SHIRT_SIZES = ['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL'];
const PANT_SIZES = [
  '28x30', '30x30', '30x32', '32x30', '32x32', '34x30', '34x32',
  '36x30', '36x32', '38x30', '38x32', '40x32',
];
const SHOE_SIZES = [
  '6', '6.5', '7', '7.5', '8', '8.5', '9', '9.5',
  '10', '10.5', '11', '11.5', '12', '13', '14',
];

const STEP_LABELS = ['Welcome', 'Sizing', 'Delivery Address', 'Department', 'Complete'];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface OnboardingWizardProps {
  profile?: ProfileData;
  companyName?: string;
}

export function OnboardingWizard({ profile, companyName }: OnboardingWizardProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [currentStep, setCurrentStep] = useState(0);

  const [formData, setFormData] = useState<WizardFormData>({
    shirtSize: profile?.shirtSize ?? '',
    pantSize: profile?.pantSize ?? '',
    shoeSize: profile?.shoeSize ?? '',
    deliveryAddressLine1: profile?.deliveryAddressLine1 ?? '',
    deliveryAddressLine2: profile?.deliveryAddressLine2 ?? '',
    deliveryCity: profile?.deliveryCity ?? '',
    deliveryState: profile?.deliveryState ?? '',
    deliveryZip: profile?.deliveryZip ?? '',
    deliveryCountry: profile?.deliveryCountry ?? '',
    department: profile?.department ?? '',
    jobTitle: profile?.jobTitle ?? '',
  });

  const updateField = useCallback(
    (field: keyof WizardFormData, value: string) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const saveProfileMutation = useMutation({
    mutationFn: async (data: Record<string, string | null>) => {
      const res = await api.put<ProfileData>('/api/v1/profiles/me', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-profile'] });
    },
  });

  const completeOnboardingMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post<ProfileData>('/api/v1/profiles/me/complete-onboarding');
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-profile'] });
      router.push('/dashboard');
    },
  });

  const buildProfilePayload = useMemo(() => {
    const payload: Record<string, string | null> = {};
    for (const [key, value] of Object.entries(formData)) {
      // Convert camelCase to snake_case for the API
      const snakeKey = key.replace(/[A-Z]/g, (m) => `_${m.toLowerCase()}`);
      payload[snakeKey] = value || null;
    }
    return payload;
  }, [formData]);

  const handleNext = async () => {
    // Save progress on each step transition
    if (currentStep > 0 && currentStep < STEP_LABELS.length - 1) {
      await saveProfileMutation.mutateAsync(buildProfilePayload);
    }
    setCurrentStep((prev) => Math.min(prev + 1, STEP_LABELS.length - 1));
  };

  const handleBack = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  };

  const handleFinish = async () => {
    await saveProfileMutation.mutateAsync(buildProfilePayload);
    await completeOnboardingMutation.mutateAsync();
  };

  const isSubmitting =
    saveProfileMutation.isPending || completeOnboardingMutation.isPending;

  return (
    <div className="flex flex-col gap-6 max-w-2xl mx-auto">
      <ProgressIndicator currentIndex={currentStep} spaceEqually>
        {STEP_LABELS.map((label) => (
          <ProgressStep key={label} label={label} />
        ))}
      </ProgressIndicator>

      <Tile className="p-6">
        {currentStep === 0 && (
          <WelcomeStep companyName={companyName} />
        )}
        {currentStep === 1 && (
          <SizingStep formData={formData} updateField={updateField} />
        )}
        {currentStep === 2 && (
          <AddressStep formData={formData} updateField={updateField} />
        )}
        {currentStep === 3 && (
          <DepartmentStep formData={formData} updateField={updateField} />
        )}
        {currentStep === 4 && (
          <CompleteStep formData={formData} />
        )}
      </Tile>

      <div className="flex items-center justify-between">
        <div>
          {currentStep > 0 && (
            <Button
              kind="secondary"
              size="md"
              onClick={handleBack}
              renderIcon={ArrowLeft}
              disabled={isSubmitting}
            >
              Back
            </Button>
          )}
        </div>

        <div className="flex items-center gap-3">
          {currentStep > 0 && currentStep < STEP_LABELS.length - 1 && (
            <Button
              kind="ghost"
              size="md"
              onClick={() =>
                setCurrentStep((prev) =>
                  Math.min(prev + 1, STEP_LABELS.length - 1),
                )
              }
              disabled={isSubmitting}
            >
              Skip
            </Button>
          )}

          {currentStep < STEP_LABELS.length - 1 ? (
            <Button
              kind="primary"
              size="md"
              onClick={handleNext}
              renderIcon={ArrowRight}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <InlineLoading description="Saving..." />
              ) : (
                'Next'
              )}
            </Button>
          ) : (
            <Button
              kind="primary"
              size="md"
              onClick={handleFinish}
              renderIcon={Checkmark}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <InlineLoading description="Finishing..." />
              ) : (
                'Finish Setup'
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step Components
// ---------------------------------------------------------------------------

function WelcomeStep({ companyName }: { companyName?: string }) {
  return (
    <div className="text-center py-6">
      <h2 className="text-2xl font-semibold text-text-primary mb-3">
        Welcome to {companyName ?? 'your'} apparel program!
      </h2>
      <p className="text-sm text-text-secondary max-w-md mx-auto">
        Let&apos;s get you set up. We&apos;ll collect your sizing information,
        delivery address, and department details so we can personalize your
        experience. You can skip any step and fill it in later.
      </p>
    </div>
  );
}

function SizingStep({
  formData,
  updateField,
}: {
  formData: WizardFormData;
  updateField: (field: keyof WizardFormData, value: string) => void;
}) {
  return (
    <div className="flex flex-col gap-5">
      <h3 className="text-lg font-semibold text-text-primary">
        Sizing Information
      </h3>
      <p className="text-sm text-text-secondary">
        Help us find the right fit for you. All fields are optional.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Dropdown
          id="shirt-size"
          titleText="Shirt Size"
          label="Select size"
          items={SHIRT_SIZES}
          selectedItem={formData.shirtSize || null}
          onChange={({ selectedItem }: { selectedItem: string | null }) =>
            updateField('shirtSize', selectedItem ?? '')
          }
        />
        <Dropdown
          id="pant-size"
          titleText="Pant Size"
          label="Select size"
          items={PANT_SIZES}
          selectedItem={formData.pantSize || null}
          onChange={({ selectedItem }: { selectedItem: string | null }) =>
            updateField('pantSize', selectedItem ?? '')
          }
        />
        <Dropdown
          id="shoe-size"
          titleText="Shoe Size"
          label="Select size"
          items={SHOE_SIZES}
          selectedItem={formData.shoeSize || null}
          onChange={({ selectedItem }: { selectedItem: string | null }) =>
            updateField('shoeSize', selectedItem ?? '')
          }
        />
      </div>
    </div>
  );
}

function AddressStep({
  formData,
  updateField,
}: {
  formData: WizardFormData;
  updateField: (field: keyof WizardFormData, value: string) => void;
}) {
  return (
    <div className="flex flex-col gap-5">
      <h3 className="text-lg font-semibold text-text-primary">
        Delivery Address
      </h3>
      <p className="text-sm text-text-secondary">
        Where should we ship your apparel? All fields are optional.
      </p>
      <TextInput
        id="address-line1"
        labelText="Address Line 1"
        value={formData.deliveryAddressLine1}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
          updateField('deliveryAddressLine1', e.target.value)
        }
      />
      <TextInput
        id="address-line2"
        labelText="Address Line 2"
        value={formData.deliveryAddressLine2}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
          updateField('deliveryAddressLine2', e.target.value)
        }
      />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <TextInput
          id="city"
          labelText="City"
          value={formData.deliveryCity}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            updateField('deliveryCity', e.target.value)
          }
        />
        <TextInput
          id="state"
          labelText="State"
          value={formData.deliveryState}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            updateField('deliveryState', e.target.value)
          }
        />
        <TextInput
          id="zip"
          labelText="ZIP Code"
          value={formData.deliveryZip}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            updateField('deliveryZip', e.target.value)
          }
        />
      </div>
      <TextInput
        id="country"
        labelText="Country"
        value={formData.deliveryCountry}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
          updateField('deliveryCountry', e.target.value)
        }
      />
    </div>
  );
}

function DepartmentStep({
  formData,
  updateField,
}: {
  formData: WizardFormData;
  updateField: (field: keyof WizardFormData, value: string) => void;
}) {
  return (
    <div className="flex flex-col gap-5">
      <h3 className="text-lg font-semibold text-text-primary">
        Department & Role
      </h3>
      <p className="text-sm text-text-secondary">
        Tell us about your position. This helps us show you relevant catalogs.
      </p>
      <TextInput
        id="department"
        labelText="Department"
        value={formData.department}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
          updateField('department', e.target.value)
        }
      />
      <TextInput
        id="job-title"
        labelText="Job Title"
        value={formData.jobTitle}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
          updateField('jobTitle', e.target.value)
        }
      />
    </div>
  );
}

function CompleteStep({ formData }: { formData: WizardFormData }) {
  const filledFields = Object.entries(formData).filter(
    ([, v]) => v !== '' && v != null,
  );

  return (
    <div className="flex flex-col gap-5">
      <h3 className="text-lg font-semibold text-text-primary">
        You&apos;re all set!
      </h3>
      <p className="text-sm text-text-secondary">
        Review your information below. Click &quot;Finish Setup&quot; to complete onboarding.
      </p>
      {filledFields.length > 0 ? (
        <div className="grid grid-cols-2 gap-3">
          {filledFields.map(([key, value]) => {
            const label = key
              .replace(/([A-Z])/g, ' $1')
              .replace(/^./, (m) => m.toUpperCase())
              .trim();
            return (
              <div key={key}>
                <p className="text-xs text-text-secondary">{label}</p>
                <p className="text-sm font-medium text-text-primary">{value}</p>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-text-secondary italic">
          No information entered yet. You can always update your profile later.
        </p>
      )}
    </div>
  );
}
