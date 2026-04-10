export type ApprovalStatus = 'pending' | 'approved' | 'rejected';

export type ApprovalEntityType = 'product' | 'catalog' | 'order' | 'bulk_order';

export interface ApprovalRequest {
  id: string;
  companyId: string;
  subBrandId: string | null;
  entityType: ApprovalEntityType;
  entityId: string;
  requestedBy: string;
  decidedBy: string | null;
  status: ApprovalStatus;
  decisionNotes: string | null;
  requestedAt: string;
  decidedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

/** Extended response for queue display — includes denormalized entity info */
export interface ApprovalQueueItem {
  id: string;
  entityType: ApprovalEntityType;
  entityId: string;
  status: ApprovalStatus;
  requestedBy: string;
  requestedAt: string;
  entityName: string;
  entityAmount: number | null;
}

export interface ApprovalRule {
  id: string;
  companyId: string;
  entityType: string;
  ruleType: string;
  thresholdAmount: number | null;
  requiredRole: string;
  isActive: boolean;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}
