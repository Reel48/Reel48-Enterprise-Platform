"""
AWS Cognito integration service.

This is the ONLY file that imports boto3. All other code calls this service
for Cognito operations. The service is injected as a FastAPI dependency,
making it easily mockable in tests.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from app.core.config import settings
from app.core.exceptions import ConflictError, ValidationError

logger = structlog.get_logger()


class CognitoService:
    """Wraps AWS Cognito AdminUser APIs via a boto3 client."""

    def __init__(self, client: Any, user_pool_id: str) -> None:
        self._client = client  # boto3 CognitoIdentityProvider client
        self._user_pool_id = user_pool_id

    def _build_user_attributes(
        self,
        email: str,
        company_id: UUID | None,
        role: str,
    ) -> list[dict[str, str]]:
        attrs = [
            {"Name": "email", "Value": email},
            {"Name": "email_verified", "Value": "true"},
            {"Name": "custom:role", "Value": role},
        ]
        if company_id is not None:
            attrs.append({"Name": "custom:company_id", "Value": str(company_id)})
        # NOTE: the custom:sub_brand_id attribute still exists in the Cognito
        # user pool (AWS does not allow deleting custom attributes) but is no
        # longer populated. The backend ignores it on login.
        return attrs

    def _extract_sub(self, response: dict[str, Any]) -> str:
        """Extract the Cognito 'sub' (UUID) from an AdminCreateUser response."""
        for attr in response["User"]["Attributes"]:
            if attr["Name"] == "sub":
                return str(attr["Value"])
        raise RuntimeError("Cognito response missing 'sub' attribute")

    async def create_cognito_user(
        self,
        email: str,
        temporary_password: str,
        company_id: UUID | None,
        role: str,
    ) -> str:
        """
        Create a Cognito user with a temporary password (admin-created flow).

        The user will be prompted to change their password on first login.
        Returns the Cognito 'sub' (UUID string).
        """
        try:
            response = self._client.admin_create_user(
                UserPoolId=self._user_pool_id,
                Username=email,
                TemporaryPassword=temporary_password,
                UserAttributes=self._build_user_attributes(email, company_id, role),
                DesiredDeliveryMediums=["EMAIL"],
            )
            return self._extract_sub(response)
        except self._client.exceptions.UsernameExistsException:
            raise ConflictError(
                f"User with email '{email}' already exists in Cognito"
            )
        except self._client.exceptions.InvalidPasswordException as e:
            raise ValidationError(str(e), field="password")

    async def create_cognito_user_with_password(
        self,
        email: str,
        password: str,
        company_id: UUID | None,
        role: str,
    ) -> str:
        """
        Create a Cognito user and set a permanent password (self-registration / invite flow).

        Uses AdminCreateUser + AdminSetUserPassword to skip the temporary password step.
        Returns the Cognito 'sub' (UUID string).
        """
        try:
            response = self._client.admin_create_user(
                UserPoolId=self._user_pool_id,
                Username=email,
                TemporaryPassword=password,
                UserAttributes=self._build_user_attributes(email, company_id, role),
                MessageAction="SUPPRESS",  # Don't send temp password email
            )
            cognito_sub = self._extract_sub(response)

            # Set the permanent password (moves user from FORCE_CHANGE_PASSWORD to CONFIRMED)
            self._client.admin_set_user_password(
                UserPoolId=self._user_pool_id,
                Username=email,
                Password=password,
                Permanent=True,
            )

            return cognito_sub
        except self._client.exceptions.UsernameExistsException:
            raise ConflictError(
                f"User with email '{email}' already exists in Cognito"
            )
        except self._client.exceptions.InvalidPasswordException as e:
            raise ValidationError(str(e), field="password")

    async def get_cognito_user(self, cognito_sub: str) -> dict[str, str] | None:
        """Fetch user attributes from Cognito by sub."""
        try:
            response = self._client.admin_get_user(
                UserPoolId=self._user_pool_id,
                Username=cognito_sub,
            )
            return {
                attr["Name"]: attr["Value"]
                for attr in response.get("UserAttributes", [])
            }
        except self._client.exceptions.UserNotFoundException:
            return None

    async def update_cognito_attributes(
        self, cognito_sub: str, attributes: dict[str, str]
    ) -> None:
        """Update custom attributes on a Cognito user."""
        user_attributes = [
            {"Name": name, "Value": value} for name, value in attributes.items()
        ]
        self._client.admin_update_user_attributes(
            UserPoolId=self._user_pool_id,
            Username=cognito_sub,
            UserAttributes=user_attributes,
        )

    async def disable_cognito_user(self, cognito_sub: str) -> None:
        """Disable a Cognito user (for soft-delete sync)."""
        try:
            self._client.admin_disable_user(
                UserPoolId=self._user_pool_id,
                Username=cognito_sub,
            )
        except self._client.exceptions.UserNotFoundException:
            logger.warning(
                "cognito_user_not_found_for_disable", cognito_sub=cognito_sub
            )


def get_cognito_service() -> CognitoService:
    """FastAPI dependency that returns a CognitoService with a real boto3 client."""
    import boto3  # type: ignore[import-untyped]

    client = boto3.client(
        "cognito-idp",
        region_name=settings.COGNITO_REGION,
    )
    return CognitoService(client, settings.COGNITO_USER_POOL_ID)
