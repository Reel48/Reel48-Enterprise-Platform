export type ApprovalStatus = 'pending' | 'approved' | 'rejected';

export type ApprovalRequestType = 'order' | 'bulk_order' | 'catalog';

export interface ApprovalRequest {
  id: string;
  requestType: ApprovalRequestType;
  status: ApprovalStatus;
  requesterId: string;
  requesterName: string;
  amount: number | null;
  reason: string | null;
  decisionById: string | null;
  decisionByName: string | null;
  decisionAt: string | null;
  decisionNotes: string | null;
  companyId: string;
  subBrandId: string;
  createdAt: string;
  updatedAt: string;
}
