"""
Tenant context model for multi-tenant request scoping.

TenantContext is extracted from the validated Cognito JWT by get_tenant_context
(in dependencies.py) and injected into every protected endpoint.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class TenantContext:
    user_id: str  # Cognito "sub" claim
    company_id: UUID | None  # None for reel48_admin (cross-company access)
    role: str  # One of: reel48_admin, company_admin, manager, employee

    @property
    def is_reel48_admin(self) -> bool:
        """Platform operator. Cross-company access."""
        return self.role == "reel48_admin"

    @property
    def is_company_admin_or_above(self) -> bool:
        """Company admin or platform admin. Use for: manage users, generate
        org codes, edit company settings, view company-wide analytics."""
        return self.role in ("reel48_admin", "company_admin")

    @property
    def is_manager_or_above(self) -> bool:
        """Manager, company admin, or platform admin. Reserved for future
        mid-tier workflows (e.g. Shopify order approvals)."""
        return self.role in ("reel48_admin", "company_admin", "manager")
