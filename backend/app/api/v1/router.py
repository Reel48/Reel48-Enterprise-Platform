from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.employee_profiles import router as employee_profiles_router
from app.api.v1.invites import router as invites_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.org_codes import router as org_codes_router
from app.api.v1.platform.analytics import router as platform_analytics_router
from app.api.v1.platform.companies import router as platform_companies_router
from app.api.v1.storage import router as storage_router
from app.api.v1.users import router as users_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_router)
v1_router.include_router(companies_router)
v1_router.include_router(org_codes_router)
v1_router.include_router(users_router)
v1_router.include_router(invites_router)
v1_router.include_router(employee_profiles_router)
v1_router.include_router(analytics_router)
v1_router.include_router(notifications_router)
v1_router.include_router(storage_router)
v1_router.include_router(platform_companies_router)
v1_router.include_router(platform_analytics_router)
