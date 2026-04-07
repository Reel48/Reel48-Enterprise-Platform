"""
Tenant context model for multi-tenant request scoping.

TenantContext is extracted from the validated Cognito JWT by get_tenant_context
(in dependencies.py) and injected into every protected endpoint. It carries
the authenticated user's identity and tenant scope, and exposes role-checking
helpers used for authorization decisions throughout the application.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class TenantContext:
    user_id: str  # Cognito "sub" claim
    company_id: UUID | None  # None for reel48_admin (cross-company access)
    sub_brand_id: UUID | None  # None for corporate_admin & reel48_admin
    role: str  # One of: reel48_admin, corporate_admin, sub_brand_admin, regional_manager, employee

    @property
    def is_reel48_admin(self) -> bool:
        """Platform operator. Cross-company access."""
        return self.role == "reel48_admin"

    @property
    def is_corporate_admin_or_above(self) -> bool:
        """Corporate admin or platform admin. Use for: manage sub-brands,
        manage all users, generate org codes, view company-wide analytics."""
        return self.role in ("reel48_admin", "corporate_admin")

    @property
    def is_admin(self) -> bool:
        """Any admin role (including sub_brand_admin). Use for: create products,
        manage catalog, approve orders. WARNING: Do NOT use for operations
        restricted to corporate_admin+ (use is_corporate_admin_or_above instead)."""
        return self.role in ("reel48_admin", "corporate_admin", "sub_brand_admin")

    @property
    def is_manager_or_above(self) -> bool:
        """Regional manager or any admin. Use for: create bulk orders, approve orders."""
        return self.role in (
            "reel48_admin",
            "corporate_admin",
            "sub_brand_admin",
            "regional_manager",
        )
