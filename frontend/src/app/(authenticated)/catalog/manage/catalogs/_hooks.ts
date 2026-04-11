import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type {
  Catalog,
  CatalogCreate,
  CatalogUpdate,
  CatalogProductEntry,
  CatalogProductAdd,
} from '@/types/catalogs';

export function useCatalogs(page: number, perPage: number, statusFilter?: string) {
  return useQuery({
    queryKey: ['catalogs', page, perPage, statusFilter],
    queryFn: async () => {
      const params: Record<string, string> = {
        page: String(page),
        per_page: String(perPage),
      };
      if (statusFilter && statusFilter !== 'all') {
        params.status = statusFilter;
      }
      return api.get<Catalog[]>('/api/v1/catalogs/', params);
    },
  });
}

export function useCatalog(id: string) {
  return useQuery({
    queryKey: ['catalogs', id],
    queryFn: async () => {
      const res = await api.get<Catalog>(`/api/v1/catalogs/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useCreateCatalog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CatalogCreate) => {
      const res = await api.post<Catalog>('/api/v1/catalogs/', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['catalogs'] });
    },
  });
}

export function useUpdateCatalog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: CatalogUpdate }) => {
      const res = await api.patch<Catalog>(`/api/v1/catalogs/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['catalogs'] });
    },
  });
}

export function useDeleteCatalog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/catalogs/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['catalogs'] });
    },
  });
}

export function useSubmitCatalog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await api.post<Catalog>(`/api/v1/catalogs/${id}/submit`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['catalogs'] });
    },
  });
}

export function useCatalogProducts(catalogId: string) {
  return useQuery({
    queryKey: ['catalogs', catalogId, 'products'],
    queryFn: async () => {
      return api.get<CatalogProductEntry[]>(`/api/v1/catalogs/${catalogId}/products/`);
    },
    enabled: !!catalogId,
  });
}

export function useAddCatalogProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ catalogId, data }: { catalogId: string; data: CatalogProductAdd }) => {
      const res = await api.post<CatalogProductEntry>(
        `/api/v1/catalogs/${catalogId}/products/`,
        data,
      );
      return res.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['catalogs', variables.catalogId, 'products'] });
    },
  });
}

export function useRemoveCatalogProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ catalogId, productId }: { catalogId: string; productId: string }) => {
      await api.delete(`/api/v1/catalogs/${catalogId}/products/${productId}`);
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['catalogs', variables.catalogId, 'products'] });
    },
  });
}
