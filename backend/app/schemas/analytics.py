from pydantic import BaseModel


class CompanyOverviewResponse(BaseModel):
    """Company-scoped analytics overview."""

    active_users: int


class PlatformOverviewResponse(BaseModel):
    """Cross-company platform metrics (reel48_admin only)."""

    total_companies: int
    total_users: int
