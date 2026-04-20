"""
Authentication endpoints — unauthenticated registration flows.

These endpoints do NOT use get_tenant_context (no JWT required).
Security is provided by rate limiting (Redis) and org code / invite token validation.
"""

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.exceptions import AppException
from app.core.rate_limit import rate_limit_auth
from app.schemas.auth import (
    InviteRegisterRequest,
    RegisterResponse,
    SelfRegisterRequest,
    ValidateOrgCodeRequest,
    ValidateOrgCodeResponse,
)
from app.schemas.common import ApiResponse
from app.services.cognito_service import CognitoService, get_cognito_service
from app.services.registration_service import RegistrationService

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/validate-org-code",
    response_model=ApiResponse[ValidateOrgCodeResponse],
)
async def validate_org_code(
    body: ValidateOrgCodeRequest,
    db: AsyncSession = Depends(get_db_session),
    _rate_limit: None = Depends(rate_limit_auth),
) -> ApiResponse[ValidateOrgCodeResponse]:
    """
    Validate an org code and return the company name.

    Unauthenticated. Rate-limited (5 attempts per IP per 15 minutes, shared with /register).
    Returns a generic 400 on any failure to prevent enumeration.
    """
    try:
        service = RegistrationService(db)
        _org_code, company = await service.validate_org_code(body.code)

        return ApiResponse(
            data=ValidateOrgCodeResponse(company_name=company.name),
        )
    except Exception:
        logger.warning("validate_org_code_failed", code=body.code)
        raise AppException(
            code="INVALID_REQUEST",
            message="Invalid registration code",
            status_code=400,
        )


@router.post(
    "/register",
    response_model=ApiResponse[RegisterResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: SelfRegisterRequest,
    db: AsyncSession = Depends(get_db_session),
    cognito_service: CognitoService = Depends(get_cognito_service),
    _rate_limit: None = Depends(rate_limit_auth),
) -> ApiResponse[RegisterResponse]:
    """
    Single-step self-registration via org code.

    Unauthenticated. Rate-limited (shared "auth" group with /validate-org-code).
    Returns a generic 400 on ANY failure to prevent enumeration.
    """
    try:
        service = RegistrationService(db)
        await service.register_via_org_code(
            code=body.code,
            email=body.email,
            full_name=body.full_name,
            password=body.password,
            cognito_service=cognito_service,
        )

        return ApiResponse(
            data=RegisterResponse(
                message="Registration successful. Please check your email to verify your account.",
            ),
        )
    except Exception:
        logger.warning("register_failed", email=body.email)
        raise AppException(
            code="REGISTRATION_FAILED",
            message="Registration failed",
            status_code=400,
        )


@router.post(
    "/register-from-invite",
    response_model=ApiResponse[RegisterResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register_from_invite(
    body: InviteRegisterRequest,
    db: AsyncSession = Depends(get_db_session),
    cognito_service: CognitoService = Depends(get_cognito_service),
) -> ApiResponse[RegisterResponse]:
    """
    Registration via invite token.

    Unauthenticated. No rate limit (tokens are single-use and time-limited).
    Returns a generic 400 on any failure.
    """
    try:
        service = RegistrationService(db)
        await service.register_via_invite(
            token=body.token,
            email=body.email,
            full_name=body.full_name,
            password=body.password,
            cognito_service=cognito_service,
        )

        return ApiResponse(
            data=RegisterResponse(
                message="Registration successful. Please check your email to verify your account.",
            ),
        )
    except Exception:
        logger.warning("register_from_invite_failed", email=body.email)
        raise AppException(
            code="REGISTRATION_FAILED",
            message="Registration failed",
            status_code=400,
        )
