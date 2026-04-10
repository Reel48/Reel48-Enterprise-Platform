import type { UserRole } from '@/types/auth';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  subBrandId: string | null;
  subBrandName?: string;
  isActive: boolean;
  createdAt: string;
}

export interface Invite {
  id: string;
  companyId: string;
  targetSubBrandId: string;
  email: string;
  role: string;
  token: string;
  expiresAt: string;
  consumedAt: string | null;
  createdBy: string;
  createdAt: string;
}

export interface OrgCode {
  id: string;
  companyId: string;
  code: string;
  isActive: boolean;
  createdBy: string;
  createdAt: string;
}

export interface SubBrand {
  id: string;
  companyId: string;
  name: string;
  slug: string;
  isDefault: boolean;
  isActive: boolean;
}
