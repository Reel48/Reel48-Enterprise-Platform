import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApprovalRule {
  id: string;
  companyId: string;
  entityType: 'order' | 'bulk_order';
  ruleType: string;
  thresholdAmount: number;
  requiredRole: string;
  isActive: boolean;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

interface CreateApprovalRulePayload {
  entityType: string;
  ruleType: string;
  thresholdAmount: number;
  requiredRole: string;
}

interface UpdateApprovalRulePayload {
  thresholdAmount?: number;
  requiredRole?: string;
  isActive?: boolean;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useApprovalRules(page: number, perPage: number) {
  return useQuery({
    queryKey: ['approval-rules', page, perPage],
    queryFn: () =>
      api.get<ApprovalRule[]>('/api/v1/approval_rules/', {
        page: String(page),
        per_page: String(perPage),
      }),
  });
}

export function useCreateApprovalRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateApprovalRulePayload) => {
      const res = await api.post<ApprovalRule>('/api/v1/approval_rules/', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-rules'] });
    },
  });
}

export function useUpdateApprovalRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateApprovalRulePayload }) => {
      const res = await api.patch<ApprovalRule>(`/api/v1/approval_rules/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-rules'] });
    },
  });
}

export function useDeleteApprovalRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/approval_rules/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-rules'] });
    },
  });
}
