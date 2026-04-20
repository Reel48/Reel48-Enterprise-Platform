"""
Seed script: Create ACME Corp. test company with a small user roster.

Usage:
    cd backend
    source .venv/bin/activate
    SEED_DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/reel48" \
      python -m scripts.seed_acme_corp

All operations are idempotent — safe to re-run.
"""

from __future__ import annotations

import asyncio
import os
import sys
from uuid import uuid4

import boto3  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.company import Company
from app.models.user import User

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COGNITO_USER_POOL_ID = "us-east-1_kpQToGvpj"
COGNITO_REGION = "us-east-1"
DEFAULT_PASSWORD = "AcmeTest1!"

ACME_COMPANY = {"name": "ACME Corp.", "slug": "acme-corp"}

# (email, full_name, role)
USERS = [
    ("acme.admin@test.reel48plus.com", "Alex Admin", "company_admin"),
    ("acme.manager@test.reel48plus.com", "Morgan Manager", "manager"),
    ("acme.employee1@test.reel48plus.com", "Eli Employee", "employee"),
    ("acme.employee2@test.reel48plus.com", "Emma Employee", "employee"),
]


async def _ensure_company(session: AsyncSession) -> Company:
    result = await session.execute(
        select(Company).where(Company.slug == ACME_COMPANY["slug"])
    )
    company = result.scalar_one_or_none()
    if company is not None:
        return company

    company = Company(name=ACME_COMPANY["name"], slug=ACME_COMPANY["slug"], is_active=True)
    session.add(company)
    await session.flush()
    return company


def _ensure_cognito_user(
    cognito_client,
    email: str,
    company_id: str,
    role: str,
) -> str:
    """Create or fetch Cognito user; return cognito_sub."""
    try:
        resp = cognito_client.admin_get_user(
            UserPoolId=COGNITO_USER_POOL_ID, Username=email
        )
        for attr in resp.get("UserAttributes", []):
            if attr["Name"] == "sub":
                return attr["Value"]
        raise RuntimeError("Cognito user missing 'sub' attribute")
    except cognito_client.exceptions.UserNotFoundException:
        pass

    create_resp = cognito_client.admin_create_user(
        UserPoolId=COGNITO_USER_POOL_ID,
        Username=email,
        TemporaryPassword=DEFAULT_PASSWORD,
        UserAttributes=[
            {"Name": "email", "Value": email},
            {"Name": "email_verified", "Value": "true"},
            {"Name": "custom:company_id", "Value": company_id},
            {"Name": "custom:role", "Value": role},
        ],
        MessageAction="SUPPRESS",
    )
    cognito_client.admin_set_user_password(
        UserPoolId=COGNITO_USER_POOL_ID,
        Username=email,
        Password=DEFAULT_PASSWORD,
        Permanent=True,
    )
    for attr in create_resp["User"]["Attributes"]:
        if attr["Name"] == "sub":
            return attr["Value"]
    raise RuntimeError("Cognito create response missing 'sub'")


async def _ensure_user(
    session: AsyncSession,
    cognito_client,
    company: Company,
    email: str,
    full_name: str,
    role: str,
) -> User:
    existing = await session.execute(select(User).where(User.email == email))
    user = existing.scalar_one_or_none()
    if user is not None:
        return user

    cognito_sub = _ensure_cognito_user(
        cognito_client, email, str(company.id), role
    )

    user = User(
        company_id=company.id,
        cognito_sub=cognito_sub or str(uuid4()),
        email=email,
        full_name=full_name,
        role=role,
        registration_method="invite",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def main() -> None:
    db_url = os.getenv("SEED_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        print("Set SEED_DATABASE_URL or DATABASE_URL first.", file=sys.stderr)
        sys.exit(1)

    cognito_client = boto3.client("cognito-idp", region_name=COGNITO_REGION)

    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        async with session.begin():
            company = await _ensure_company(session)
            for email, full_name, role in USERS:
                user = await _ensure_user(
                    session, cognito_client, company, email, full_name, role
                )
                print(f"  user: {user.email} ({user.role})")

    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
