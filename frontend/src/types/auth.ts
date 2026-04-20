export type UserRole =
  | 'reel48_admin'
  | 'company_admin'
  | 'manager'
  | 'employee';

export interface TenantContext {
  userId: string;
  companyId: string | null;
  role: UserRole;
}

export interface AuthUser {
  email: string;
  fullName: string;
  companyName: string;
  tenantContext: TenantContext;
}

export type AuthState = 'loading' | 'authenticated' | 'unauthenticated';
