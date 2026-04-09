from uuid import UUID

from pydantic import BaseModel


class SpendSummaryResponse(BaseModel):
    """Aggregate spend across individual and bulk orders."""

    total_spend: float
    order_count: int
    average_order_value: float
    individual_order_spend: float
    bulk_order_spend: float


class SubBrandSpendResponse(BaseModel):
    """Single item in the sub-brand spend breakdown."""

    sub_brand_id: UUID
    sub_brand_name: str
    total_spend: float
    order_count: int


class SpendOverTimeResponse(BaseModel):
    """Single time-bucket entry for trend charting."""

    period: str
    total_spend: float
    order_count: int


class OrderStatusBreakdownResponse(BaseModel):
    """Single status group entry."""

    status: str
    count: int
    order_type: str  # "individual" or "bulk"


class TopProductResponse(BaseModel):
    """Single product ranking entry."""

    product_id: UUID
    product_name: str
    product_sku: str
    total_quantity: int
    total_revenue: float


class SizeDistributionResponse(BaseModel):
    """Single size entry in the distribution."""

    size: str
    count: int
    percentage: float


class InvoiceStatusBreakdown(BaseModel):
    """Invoice count and total by status."""

    status: str
    count: int
    total: float


class InvoiceBillingFlowBreakdown(BaseModel):
    """Invoice count and total by billing flow."""

    billing_flow: str
    count: int
    total: float


class InvoiceSummaryResponse(BaseModel):
    """Invoice totals by status and billing flow."""

    total_invoiced: float
    total_paid: float
    total_outstanding: float
    invoice_count: int
    by_status: list[InvoiceStatusBreakdown]
    by_billing_flow: list[InvoiceBillingFlowBreakdown]


class ApprovalMetricsResponse(BaseModel):
    """Approval request metrics."""

    pending_count: int
    approved_count: int
    rejected_count: int
    approval_rate: float
    avg_approval_time_hours: float | None


class PlatformOverviewResponse(BaseModel):
    """Cross-company platform metrics (reel48_admin only)."""

    total_companies: int
    total_sub_brands: int
    total_users: int
    total_orders: int
    total_revenue: float
    active_catalogs: int


class CompanyRevenueResponse(BaseModel):
    """Single company revenue entry."""

    company_id: UUID
    company_name: str
    total_revenue: float
    invoice_count: int
