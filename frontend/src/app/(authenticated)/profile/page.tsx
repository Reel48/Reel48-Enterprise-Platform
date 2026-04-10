'use client';

import { useState } from 'react';
import {
  Button,
  Dropdown,
  InlineNotification,
  TextInput,
  Tile,
  ToastNotification,
} from '@carbon/react';
import { Save, TrashCan, Upload } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { useAuth } from '@/lib/auth/hooks';
import { api } from '@/lib/api/client';
import { useFileUpload } from '@/hooks/useStorage';
import { S3Image } from '@/components/ui/S3Image';
import type { Profile } from '@/types/profiles';
import { SHIRT_SIZES, PANT_SIZES, SHOE_SIZES } from '@/types/profiles';

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useMyProfile() {
  return useQuery({
    queryKey: ['my-profile'],
    queryFn: async () => {
      const res = await api.get<Profile>('/api/v1/profiles/me');
      return res.data;
    },
  });
}

function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Profile>) => {
      const res = await api.put<Profile>('/api/v1/profiles/me', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-profile'] });
    },
  });
}

function useDeleteProfilePhoto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.delete('/api/v1/profiles/me/photo');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-profile'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const PROFILE_FIELDS: (keyof Profile)[] = [
  'shirtSize',
  'pantSize',
  'shoeSize',
  'deliveryAddressLine1',
  'department',
  'jobTitle',
];

function calculateCompleteness(profile: Profile | undefined): number {
  if (!profile) return 0;
  const filled = PROFILE_FIELDS.filter(
    (f) => profile[f] != null && profile[f] !== '',
  ).length;
  return Math.round((filled / PROFILE_FIELDS.length) * 100);
}

function toDropdownItem(value: string) {
  return { id: value, text: value };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ProfilePage() {
  const { user } = useAuth();
  const { data: profile, isLoading, isError } = useMyProfile();
  const updateProfile = useUpdateProfile();
  const deletePhoto = useDeleteProfilePhoto();
  const fileUpload = useFileUpload();
  const queryClient = useQueryClient();

  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  // Form state — initialized from profile
  const [department, setDepartment] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [shirtSize, setShirtSize] = useState('');
  const [pantSize, setPantSize] = useState('');
  const [shoeSize, setShoeSize] = useState('');
  const [addressLine1, setAddressLine1] = useState('');
  const [addressLine2, setAddressLine2] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [zip, setZip] = useState('');
  const [initialized, setInitialized] = useState(false);

  // Sync form state from profile data on first load
  if (profile && !initialized) {
    setDepartment(profile.department ?? '');
    setJobTitle(profile.jobTitle ?? '');
    setShirtSize(profile.shirtSize ?? '');
    setPantSize(profile.pantSize ?? '');
    setShoeSize(profile.shoeSize ?? '');
    setAddressLine1(profile.deliveryAddressLine1 ?? '');
    setAddressLine2(profile.deliveryAddressLine2 ?? '');
    setCity(profile.deliveryCity ?? '');
    setState(profile.deliveryState ?? '');
    setZip(profile.deliveryZip ?? '');
    setInitialized(true);
  }

  const handleSave = () => {
    updateProfile.mutate(
      {
        department: department || null,
        jobTitle: jobTitle || null,
        shirtSize: shirtSize || null,
        pantSize: pantSize || null,
        shoeSize: shoeSize || null,
        deliveryAddressLine1: addressLine1 || null,
        deliveryAddressLine2: addressLine2 || null,
        deliveryCity: city || null,
        deliveryState: state || null,
        deliveryZip: zip || null,
      },
      {
        onSuccess: () => {
          setToast({ kind: 'success', message: 'Profile updated successfully' });
          setTimeout(() => setToast(null), 3000);
        },
        onError: () => {
          setToast({ kind: 'error', message: 'Failed to update profile' });
          setTimeout(() => setToast(null), 3000);
        },
      },
    );
  };

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    fileUpload.mutate(
      { file, category: 'profiles' },
      {
        onSuccess: async (s3Key) => {
          await api.post('/api/v1/profiles/me/photo', { s3Key });
          queryClient.invalidateQueries({ queryKey: ['my-profile'] });
          setToast({ kind: 'success', message: 'Photo uploaded successfully' });
          setTimeout(() => setToast(null), 3000);
        },
        onError: () => {
          setToast({ kind: 'error', message: 'Failed to upload photo' });
          setTimeout(() => setToast(null), 3000);
        },
      },
    );
  };

  const handleDeletePhoto = () => {
    deletePhoto.mutate(undefined, {
      onSuccess: () => {
        setToast({ kind: 'success', message: 'Photo removed' });
        setTimeout(() => setToast(null), 3000);
      },
    });
  };

  if (isLoading) {
    return (
      <div className="py-12 text-center text-text-secondary">
        Loading profile...
      </div>
    );
  }

  if (isError || !profile) {
    return (
      <InlineNotification
        kind="error"
        title="Failed to load profile"
        subtitle="Please try refreshing the page."
        hideCloseButton
      />
    );
  }

  const completeness = calculateCompleteness(profile);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">
            My Profile
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            {completeness}% complete
          </p>
        </div>
        <Button
          kind="primary"
          renderIcon={Save}
          onClick={handleSave}
          disabled={updateProfile.isPending}
        >
          {updateProfile.isPending ? 'Saving...' : 'Save Changes'}
        </Button>
      </div>

      {/* Profile Photo */}
      <Tile>
        <h2 className="text-base font-semibold text-text-primary mb-4">
          Profile Photo
        </h2>
        <div className="flex items-center gap-6">
          <div className="flex-shrink-0 rounded-full overflow-hidden">
            <S3Image
              s3Key={profile.profilePhotoUrl}
              alt="Profile photo"
              width={96}
              height={96}
              className="rounded-full object-cover"
            />
          </div>
          <div className="flex gap-2">
            <label>
              <Button
                kind="secondary"
                size="sm"
                renderIcon={Upload}
                as="span"
                disabled={fileUpload.isPending}
              >
                {fileUpload.isPending ? 'Uploading...' : 'Upload Photo'}
              </Button>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={handlePhotoUpload}
                className="hidden"
              />
            </label>
            {profile.profilePhotoUrl && (
              <Button
                kind="danger--ghost"
                size="sm"
                renderIcon={TrashCan}
                onClick={handleDeletePhoto}
                disabled={deletePhoto.isPending}
              >
                Remove
              </Button>
            )}
          </div>
        </div>
      </Tile>

      {/* Personal Info */}
      <Tile>
        <h2 className="text-base font-semibold text-text-primary mb-4">
          Personal Information
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <TextInput
            id="fullName"
            labelText="Full Name"
            value={user?.fullName ?? ''}
            readOnly
            disabled
          />
          <TextInput
            id="email"
            labelText="Email"
            value={user?.email ?? ''}
            readOnly
            disabled
          />
          <TextInput
            id="department"
            labelText="Department"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
          />
          <TextInput
            id="jobTitle"
            labelText="Job Title"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
          />
        </div>
      </Tile>

      {/* Sizing */}
      <Tile>
        <h2 className="text-base font-semibold text-text-primary mb-4">
          Sizing
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Dropdown
            id="shirtSize"
            titleText="Shirt Size"
            label="Select size"
            items={SHIRT_SIZES.map(toDropdownItem)}
            itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
            selectedItem={shirtSize ? toDropdownItem(shirtSize) : null}
            onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) =>
              setShirtSize(selectedItem?.id ?? '')
            }
          />
          <Dropdown
            id="pantSize"
            titleText="Pant Size"
            label="Select size"
            items={PANT_SIZES.map(toDropdownItem)}
            itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
            selectedItem={pantSize ? toDropdownItem(pantSize) : null}
            onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) =>
              setPantSize(selectedItem?.id ?? '')
            }
          />
          <Dropdown
            id="shoeSize"
            titleText="Shoe Size"
            label="Select size"
            items={SHOE_SIZES.map(toDropdownItem)}
            itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
            selectedItem={shoeSize ? toDropdownItem(shoeSize) : null}
            onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) =>
              setShoeSize(selectedItem?.id ?? '')
            }
          />
        </div>
      </Tile>

      {/* Delivery Address */}
      <Tile>
        <h2 className="text-base font-semibold text-text-primary mb-4">
          Delivery Address
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <TextInput
            id="addressLine1"
            labelText="Address Line 1"
            value={addressLine1}
            onChange={(e) => setAddressLine1(e.target.value)}
          />
          <TextInput
            id="addressLine2"
            labelText="Address Line 2"
            value={addressLine2}
            onChange={(e) => setAddressLine2(e.target.value)}
          />
          <TextInput
            id="city"
            labelText="City"
            value={city}
            onChange={(e) => setCity(e.target.value)}
          />
          <div className="grid grid-cols-2 gap-4">
            <TextInput
              id="state"
              labelText="State"
              value={state}
              onChange={(e) => setState(e.target.value)}
            />
            <TextInput
              id="zip"
              labelText="ZIP Code"
              value={zip}
              onChange={(e) => setZip(e.target.value)}
            />
          </div>
        </div>
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
