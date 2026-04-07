from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")

# Sub-routers will be included here as modules are built:
# v1_router.include_router(auth_router)
# v1_router.include_router(companies_router)
# v1_router.include_router(sub_brands_router)
# v1_router.include_router(users_router)
# v1_router.include_router(invites_router)
# v1_router.include_router(org_codes_router)
# v1_router.include_router(platform_router)
