'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Loading } from '@carbon/react';

import { api } from '@/lib/api/client';
import { OnboardingWizard } from '@/components/features/engagement/OnboardingWizard';

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

export default function OnboardingPage() {
  const router = useRouter();

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['my-profile-onboarding'],
    queryFn: async () => {
      try {
        const res = await api.get<ProfileData>('/api/v1/profiles/me');
        return res.data;
      } catch {
        // No profile yet — that's fine, wizard will create one
        return null;
      }
    },
  });

  // Redirect if onboarding is already complete
  useEffect(() => {
    if (profile?.onboardingComplete) {
      router.replace('/dashboard');
    }
  }, [profile?.onboardingComplete, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loading withOverlay={false} description="Loading..." />
      </div>
    );
  }

  if (profile?.onboardingComplete) {
    return null; // Will redirect
  }

  return (
    <div className="py-6">
      <OnboardingWizard profile={profile ?? undefined} />
    </div>
  );
}
