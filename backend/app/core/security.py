"""
JWT validation and JWKS key management for Amazon Cognito.

Validates Cognito ID tokens by:
1. Fetching and caching the JWKS (JSON Web Key Set) from the Cognito user pool
2. Matching the token's `kid` header to a key in the JWKS
3. Decoding and verifying the token (signature, expiry, audience, issuer)
4. Confirming the token is an ID token (carries custom attributes)

The _fetch_jwks function is the test seam — tests monkeypatch it to return
a JWKS containing a test RSA public key, avoiding real HTTP calls to Cognito.
"""

import time
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

# --- JWKS cache (module-level) ---
_jwks_keys: list[dict[str, Any]] | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS: float = 86400.0  # 24 hours


async def _fetch_jwks() -> list[dict[str, Any]]:
    """Fetch the JWKS key set from Cognito. This is the test seam."""
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.cognito_jwks_url, timeout=10.0)
        response.raise_for_status()
        keys: list[dict[str, Any]] = response.json()["keys"]
        return keys


async def _get_jwks_keys(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Return cached JWKS keys, refreshing if stale or forced."""
    global _jwks_keys, _jwks_fetched_at  # noqa: PLW0603

    now = time.monotonic()
    if _jwks_keys is None or force_refresh or (now - _jwks_fetched_at) > _JWKS_TTL_SECONDS:
        _jwks_keys = await _fetch_jwks()
        _jwks_fetched_at = now

    return _jwks_keys


async def _get_signing_key(kid: str) -> dict[str, Any]:
    """Find the JWKS key matching the token's kid. Re-fetches once on miss (key rotation)."""
    keys = await _get_jwks_keys()

    for key in keys:
        if key.get("kid") == kid:
            return key

    # Key not found — might be a rotation. Force one re-fetch.
    keys = await _get_jwks_keys(force_refresh=True)
    for key in keys:
        if key.get("kid") == kid:
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )


async def validate_cognito_token(token: str) -> dict[str, Any]:
    """
    Validate a Cognito ID token and return the decoded claims.

    Raises HTTPException(401) on any validation failure. Error messages are
    intentionally generic to avoid information leakage.
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    signing_key = await _get_signing_key(kid)

    try:
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.COGNITO_CLIENT_ID,
            issuer=settings.cognito_issuer,
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Cognito ID tokens carry custom attributes; access tokens don't.
    if claims.get("token_use") != "id":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Ensure the required custom claim is present
    if "custom:role" not in claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    result: dict[str, Any] = claims
    return result
