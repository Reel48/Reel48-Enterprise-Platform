from fastapi import APIRouter

from app.api.v1.approval_rules import router as approval_rules_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.employee_profiles import router as employee_profiles_router
from app.api.v1.invites import router as invites_router
from app.api.v1.invoices import router as invoices_router
from app.api.v1.catalogs import router as catalogs_router
from app.api.v1.bulk_orders import router as bulk_orders_router
from app.api.v1.orders import router as orders_router
from app.api.v1.products import router as products_router
from app.api.v1.org_codes import router as org_codes_router
from app.api.v1.platform.catalogs import router as platform_catalogs_router
from app.api.v1.platform.bulk_orders import router as platform_bulk_orders_router
from app.api.v1.platform.orders import router as platform_orders_router
from app.api.v1.platform.approval_rules import router as platform_approval_rules_router
from app.api.v1.platform.approvals import router as platform_approvals_router
from app.api.v1.platform.analytics import router as platform_analytics_router
from app.api.v1.platform.invoices import router as platform_invoices_router
from app.api.v1.platform.companies import router as platform_companies_router
from app.api.v1.platform.products import router as platform_products_router
from app.api.v1.sub_brands import router as sub_brands_router
from app.api.v1.users import router as users_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.storage import router as storage_router
from app.api.v1.wishlists import router as wishlists_router
from app.api.v1.webhooks import router as webhooks_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_router)
v1_router.include_router(companies_router)
v1_router.include_router(sub_brands_router)
v1_router.include_router(org_codes_router)
v1_router.include_router(users_router)
v1_router.include_router(invites_router)
v1_router.include_router(employee_profiles_router)
v1_router.include_router(products_router)
v1_router.include_router(catalogs_router)
v1_router.include_router(orders_router)
v1_router.include_router(bulk_orders_router)
v1_router.include_router(approvals_router)
v1_router.include_router(approval_rules_router)
v1_router.include_router(invoices_router)
v1_router.include_router(platform_companies_router)
v1_router.include_router(platform_products_router)
v1_router.include_router(platform_catalogs_router)
v1_router.include_router(platform_orders_router)
v1_router.include_router(platform_bulk_orders_router)
v1_router.include_router(platform_approvals_router)
v1_router.include_router(platform_approval_rules_router)
v1_router.include_router(platform_invoices_router)
v1_router.include_router(platform_analytics_router)
v1_router.include_router(analytics_router)
v1_router.include_router(notifications_router)
v1_router.include_router(storage_router)
v1_router.include_router(wishlists_router)
v1_router.include_router(webhooks_router)
