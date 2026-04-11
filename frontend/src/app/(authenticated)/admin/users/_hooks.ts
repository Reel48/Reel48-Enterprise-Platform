import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api, ApiRequestError } from '@/lib/api/client';

import type { User, Invite, OrgCode, SubBrand } from './_types';

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export function useUsers(page: number, perPage: number, roleFilter: string) {
  const params: Record<string, string> = {
    page: String(page),
    per_page: String(perPage),
  };
  if (roleFilter !== 'all') params.role = roleFilter;

  return useQuery({
    queryKey: ['users', page, perPage, roleFilter],
    queryFn: () => api.get<User[]>('/api/v1/users/', params),
  });
}

export function useDeactivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.delete(`/api/v1/users/${userId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: Record<string, unknown> }) =>
      api.patch<User>(`/api/v1/users/${userId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Sub-Brands (for invite modal dropdown)
// ---------------------------------------------------------------------------

export function useSubBrands() {
  return useQuery({
    queryKey: ['sub-brands'],
    queryFn: () => api.get<SubBrand[]>('/api/v1/sub_brands/'),
    staleTime: 5 * 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// Invites
// ---------------------------------------------------------------------------

export function useInvites(page: number, perPage: number) {
  return useQuery({
    queryKey: ['invites', page, perPage],
    queryFn: () =>
      api.get<Invite[]>('/api/v1/invites/', {
        page: String(page),
        per_page: String(perPage),
      }),
  });
}

export function useCreateInvite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { email: string; targetSubBrandId: string; role: string }) =>
      api.post('/api/v1/invites/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invites'] });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

export function useDeleteInvite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: string) => api.delete(`/api/v1/invites/${inviteId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invites'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Org Codes
// ---------------------------------------------------------------------------

export function useCurrentOrgCode() {
  return useQuery({
    queryKey: ['org-code-current'],
    queryFn: async () => {
      try {
        const res = await api.get<OrgCode>('/api/v1/org_codes/current');
        return res.data;
      } catch (err) {
        if (err instanceof ApiRequestError && err.status === 404) {
          return null;
        }
        throw err;
      }
    },
    retry: (failureCount, error) => {
      if (error instanceof ApiRequestError && error.status === 404) return false;
      return failureCount < 3;
    },
  });
}

export function useGenerateOrgCode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<OrgCode>('/api/v1/org_codes/'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-code-current'] });
    },
  });
}

export function useDeactivateOrgCode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orgCodeId: string) => api.delete(`/api/v1/org_codes/${orgCodeId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-code-current'] });
    },
  });
}
