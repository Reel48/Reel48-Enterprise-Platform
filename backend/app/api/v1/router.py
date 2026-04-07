from fastapi import APIRouter

from app.api.v1.companies import router as companies_router
from app.api.v1.invites import router as invites_router
from app.api.v1.org_codes import router as org_codes_router
from app.api.v1.sub_brands import router as sub_brands_router
from app.api.v1.users import router as users_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(companies_router)
v1_router.include_router(sub_brands_router)
v1_router.include_router(org_codes_router)
v1_router.include_router(users_router)
v1_router.include_router(invites_router)

# Future sub-routers:
# v1_router.include_router(auth_router)
# v1_router.include_router(platform_router)
