export type UserRole =
  | 'reel48_admin'
  | 'corporate_admin'
  | 'sub_brand_admin'
  | 'regional_manager'
  | 'employee';

export interface TenantContext {
  userId: string;
  companyId: string | null;
  subBrandId: string | null;
  role: UserRole;
}

export interface AuthUser {
  email: string;
  fullName: string;
  tenantContext: TenantContext;
}

export type AuthState = 'loading' | 'authenticated' | 'unauthenticated';
