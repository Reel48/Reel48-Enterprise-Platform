"""
Seed script: Create ACME Corp. test company with users, products, and catalogs.

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
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import boto3  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure the backend package is importable when running as a module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.base import Base
from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.company import Company
from app.models.employee_profile import EmployeeProfile
from app.models.product import Product
from app.models.sub_brand import SubBrand
from app.models.user import User

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COGNITO_USER_POOL_ID = "us-east-1_kpQToGvpj"
COGNITO_REGION = "us-east-1"
DEFAULT_PASSWORD = "AcmeTest1!"

# Existing reel48_admin user ID (used as approved_by for products/catalogs)
REEL48_ADMIN_USER_ID = UUID("29615b08-ead3-44f4-95f9-638cc69e01d2")

ACME_COMPANY = {"name": "ACME Corp.", "slug": "acme-corp"}

SUB_BRANDS = [
    {"name": "ACME North", "slug": "acme-north", "is_default": True},
    {"name": "ACME South", "slug": "acme-south", "is_default": False},
]

# Users: (email, full_name, role, sub_brand_index_or_None, department, job_title, location, shirt_size)
USERS = [
    ("acme.admin@test.reel48plus.com", "Alex Admin", "corporate_admin", None, "Executive", "Corporate Administrator", "Chicago, IL", "L"),
    ("acme.north.admin@test.reel48plus.com", "Nora North", "sub_brand_admin", 0, "Management", "North Brand Admin", "Detroit, MI", "M"),
    ("acme.south.admin@test.reel48plus.com", "Sam South", "sub_brand_admin", 1, "Management", "South Brand Admin", "Atlanta, GA", "L"),
    ("acme.north.manager@test.reel48plus.com", "Mike Manager", "regional_manager", 0, "Operations", "Regional Manager", "Detroit, MI", "XL"),
    ("john.doe@test.reel48plus.com", "John Doe", "employee", 0, "Sales", "Sales Associate", "Detroit, MI", "L"),
    ("jane.smith@test.reel48plus.com", "Jane Smith", "employee", 0, "Marketing", "Marketing Coordinator", "Ann Arbor, MI", "S"),
    ("bob.jones@test.reel48plus.com", "Bob Jones", "employee", 1, "Warehouse", "Warehouse Associate", "Atlanta, GA", "XL"),
]

# Products: (sku, name, description, price, sizes, decorations, sub_brand_index)
PRODUCTS = [
    (
        "ACME-N-POLO-001",
        "ACME North Polo Shirt",
        "Classic polo shirt with ACME North branding. Moisture-wicking performance fabric.",
        Decimal("29.99"),
        ["S", "M", "L", "XL", "2XL"],
        ["Embroidered Logo", "Screen Print"],
        0,
    ),
    (
        "ACME-N-CAP-001",
        "ACME North Baseball Cap",
        "Adjustable baseball cap with embroidered ACME North logo.",
        Decimal("14.99"),
        ["One Size"],
        ["Embroidered Logo"],
        0,
    ),
    (
        "ACME-S-JACKET-001",
        "ACME South Windbreaker",
        "Lightweight windbreaker with ACME South branding. Water-resistant shell.",
        Decimal("59.99"),
        ["S", "M", "L", "XL"],
        ["Embroidered Logo", "Heat Transfer"],
        1,
    ),
    (
        "ACME-S-TEE-001",
        "ACME South T-Shirt",
        "Soft cotton t-shirt with ACME South screen print logo.",
        Decimal("19.99"),
        ["S", "M", "L", "XL", "2XL", "3XL"],
        ["Screen Print"],
        1,
    ),
]

# Catalogs: (name, slug, payment_model, sub_brand_index, has_buying_window)
CATALOGS = [
    ("ACME North Spring 2026", "acme-north-spring-2026", "self_service", 0, False),
    ("ACME South Spring 2026", "acme-south-spring-2026", "invoice_after_close", 1, True),
]


# ---------------------------------------------------------------------------
# Cognito helpers
# ---------------------------------------------------------------------------


def create_cognito_user(
    client,
    email: str,
    password: str,
    company_id: UUID | None,
    sub_brand_id: UUID | None,
    role: str,
) -> str:
    """Create a Cognito user with a permanent password. Returns cognito sub."""
    attrs = [
        {"Name": "email", "Value": email},
        {"Name": "email_verified", "Value": "true"},
        {"Name": "custom:role", "Value": role},
    ]
    if company_id is not None:
        attrs.append({"Name": "custom:company_id", "Value": str(company_id)})
    if sub_brand_id is not None:
        attrs.append({"Name": "custom:sub_brand_id", "Value": str(sub_brand_id)})

    try:
        response = client.admin_create_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=email,
            TemporaryPassword=password,
            UserAttributes=attrs,
            MessageAction="SUPPRESS",
        )
        cognito_sub = _extract_sub(response)
        # Set permanent password (moves from FORCE_CHANGE_PASSWORD to CONFIRMED)
        client.admin_set_user_password(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=email,
            Password=password,
            Permanent=True,
        )
        print(f"  [CREATE] Cognito user: {email}")
        return cognito_sub
    except client.exceptions.UsernameExistsException:
        # User already exists — look up their sub
        cognito_sub = _lookup_cognito_sub(client, email)
        print(f"  [SKIP]   Cognito user already exists: {email}")
        return cognito_sub


def _extract_sub(response: dict) -> str:
    for attr in response["User"]["Attributes"]:
        if attr["Name"] == "sub":
            return str(attr["Value"])
    raise RuntimeError("Cognito response missing 'sub' attribute")


def _lookup_cognito_sub(client, email: str) -> str:
    response = client.admin_get_user(
        UserPoolId=COGNITO_USER_POOL_ID,
        Username=email,
    )
    for attr in response.get("UserAttributes", []):
        if attr["Name"] == "sub":
            return str(attr["Value"])
    raise RuntimeError(f"Could not find 'sub' for Cognito user {email}")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


async def get_or_create_company(session: AsyncSession) -> Company:
    result = await session.execute(
        select(Company).where(Company.slug == ACME_COMPANY["slug"])
    )
    company = result.scalar_one_or_none()
    if company:
        print(f"  [SKIP]   Company already exists: {company.name} ({company.id})")
        return company

    company = Company(
        id=uuid4(),
        name=ACME_COMPANY["name"],
        slug=ACME_COMPANY["slug"],
        is_active=True,
    )
    session.add(company)
    await session.flush()
    await session.refresh(company)
    print(f"  [CREATE] Company: {company.name} ({company.id})")
    return company


async def get_or_create_sub_brand(
    session: AsyncSession,
    company_id: UUID,
    name: str,
    slug: str,
    is_default: bool,
) -> SubBrand:
    result = await session.execute(
        select(SubBrand).where(
            SubBrand.company_id == company_id,
            SubBrand.slug == slug,
        )
    )
    sb = result.scalar_one_or_none()
    if sb:
        print(f"  [SKIP]   Sub-brand already exists: {sb.name} ({sb.id})")
        return sb

    sb = SubBrand(
        id=uuid4(),
        company_id=company_id,
        name=name,
        slug=slug,
        is_default=is_default,
        is_active=True,
    )
    session.add(sb)
    await session.flush()
    await session.refresh(sb)
    print(f"  [CREATE] Sub-brand: {sb.name} ({sb.id})")
    return sb


async def get_or_create_db_user(
    session: AsyncSession,
    cognito_sub: str,
    email: str,
    full_name: str,
    role: str,
    company_id: UUID,
    sub_brand_id: UUID | None,
) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        print(f"  [SKIP]   DB user already exists: {email} ({user.id})")
        return user

    user = User(
        id=uuid4(),
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        cognito_sub=cognito_sub,
        email=email,
        full_name=full_name,
        role=role,
        registration_method="invite",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    print(f"  [CREATE] DB user: {email} ({user.id})")
    return user


async def get_or_create_profile(
    session: AsyncSession,
    user: User,
    company_id: UUID,
    sub_brand_id: UUID | None,
    department: str,
    job_title: str,
    location: str,
    shirt_size: str,
) -> EmployeeProfile:
    result = await session.execute(
        select(EmployeeProfile).where(EmployeeProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile:
        print(f"  [SKIP]   Profile already exists for: {user.email}")
        return profile

    profile = EmployeeProfile(
        id=uuid4(),
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        user_id=user.id,
        department=department,
        job_title=job_title,
        location=location,
        shirt_size=shirt_size,
        onboarding_complete=True,
    )
    session.add(profile)
    await session.flush()
    await session.refresh(profile)
    print(f"  [CREATE] Profile for: {user.email}")
    return profile


async def get_or_create_product(
    session: AsyncSession,
    company_id: UUID,
    sub_brand_id: UUID,
    created_by: UUID,
    approved_by: UUID,
    sku: str,
    name: str,
    description: str,
    unit_price: Decimal,
    sizes: list[str],
    decoration_options: list[str],
) -> Product:
    result = await session.execute(
        select(Product).where(
            Product.company_id == company_id,
            Product.sku == sku,
        )
    )
    product = result.scalar_one_or_none()
    if product:
        print(f"  [SKIP]   Product already exists: {sku}")
        return product

    now = datetime.now(timezone.utc)
    product = Product(
        id=uuid4(),
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=name,
        description=description,
        sku=sku,
        unit_price=unit_price,
        sizes=sizes,
        decoration_options=decoration_options,
        image_urls=[],
        status="active",
        approved_by=approved_by,
        approved_at=now,
        created_by=created_by,
    )
    session.add(product)
    await session.flush()
    await session.refresh(product)
    print(f"  [CREATE] Product: {name} ({sku})")
    return product


async def get_or_create_catalog(
    session: AsyncSession,
    company_id: UUID,
    sub_brand_id: UUID,
    created_by: UUID,
    approved_by: UUID,
    name: str,
    slug: str,
    payment_model: str,
    has_buying_window: bool,
) -> Catalog:
    result = await session.execute(
        select(Catalog).where(
            Catalog.company_id == company_id,
            Catalog.slug == slug,
        )
    )
    catalog = result.scalar_one_or_none()
    if catalog:
        print(f"  [SKIP]   Catalog already exists: {slug}")
        return catalog

    now = datetime.now(timezone.utc)
    catalog = Catalog(
        id=uuid4(),
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=name,
        description=f"{name} — browse and order branded apparel.",
        slug=slug,
        payment_model=payment_model,
        status="active",
        buying_window_opens_at=now if has_buying_window else None,
        buying_window_closes_at=(now + timedelta(days=30)) if has_buying_window else None,
        approved_by=approved_by,
        approved_at=now,
        created_by=created_by,
    )
    session.add(catalog)
    await session.flush()
    await session.refresh(catalog)
    print(f"  [CREATE] Catalog: {name} ({slug})")
    return catalog


async def link_catalog_product(
    session: AsyncSession,
    catalog: Catalog,
    product: Product,
    display_order: int,
) -> None:
    result = await session.execute(
        select(CatalogProduct).where(
            CatalogProduct.catalog_id == catalog.id,
            CatalogProduct.product_id == product.id,
        )
    )
    if result.scalar_one_or_none():
        print(f"  [SKIP]   Link already exists: {catalog.slug} ↔ {product.sku}")
        return

    cp = CatalogProduct(
        id=uuid4(),
        company_id=catalog.company_id,
        sub_brand_id=catalog.sub_brand_id,
        catalog_id=catalog.id,
        product_id=product.id,
        display_order=display_order,
    )
    session.add(cp)
    await session.flush()
    print(f"  [CREATE] Link: {catalog.slug} ↔ {product.sku}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    db_url = os.environ.get("SEED_DATABASE_URL")
    if not db_url:
        print("ERROR: SEED_DATABASE_URL environment variable is required.")
        print('Example: SEED_DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/reel48"')
        sys.exit(1)

    print("=" * 60)
    print("  ACME Corp. Seed Script")
    print("=" * 60)
    print()

    # Database setup
    engine = create_async_engine(db_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Cognito client
    cognito_client = boto3.client("cognito-idp", region_name=COGNITO_REGION)

    async with SessionLocal() as session:
        # -- Step 1: Company --
        print("[1/7] Company")
        company = await get_or_create_company(session)
        await session.commit()

        # -- Step 2: Sub-brands --
        print("\n[2/7] Sub-brands")
        sub_brands: list[SubBrand] = []
        for sb_def in SUB_BRANDS:
            sb = await get_or_create_sub_brand(
                session, company.id, sb_def["name"], sb_def["slug"], sb_def["is_default"]
            )
            sub_brands.append(sb)
        await session.commit()

        # -- Step 3: Cognito + DB users --
        print("\n[3/7] Users (Cognito + Database)")
        users: list[User] = []
        for email, full_name, role, sb_idx, dept, title, loc, shirt in USERS:
            sub_brand_id = sub_brands[sb_idx].id if sb_idx is not None else None

            cognito_sub = create_cognito_user(
                cognito_client, email, DEFAULT_PASSWORD, company.id, sub_brand_id, role
            )

            user = await get_or_create_db_user(
                session, cognito_sub, email, full_name, role, company.id, sub_brand_id
            )
            users.append(user)
        await session.commit()

        # -- Step 4: Employee profiles --
        print("\n[4/7] Employee profiles")
        for i, (email, full_name, role, sb_idx, dept, title, loc, shirt) in enumerate(USERS):
            sub_brand_id = sub_brands[sb_idx].id if sb_idx is not None else None
            await get_or_create_profile(
                session, users[i], company.id, sub_brand_id, dept, title, loc, shirt
            )
        await session.commit()

        # -- Step 5: Products --
        print("\n[5/7] Products")
        # Find the sub-brand admin user IDs for created_by
        sb_admin_users = {0: users[1], 1: users[2]}  # Nora North, Sam South

        products: list[Product] = []
        for sku, name, desc, price, sizes, decorations, sb_idx in PRODUCTS:
            product = await get_or_create_product(
                session,
                company_id=company.id,
                sub_brand_id=sub_brands[sb_idx].id,
                created_by=sb_admin_users[sb_idx].id,
                approved_by=REEL48_ADMIN_USER_ID,
                sku=sku,
                name=name,
                description=desc,
                unit_price=price,
                sizes=sizes,
                decoration_options=decorations,
            )
            products.append(product)
        await session.commit()

        # -- Step 6: Catalogs --
        print("\n[6/7] Catalogs")
        catalogs: list[Catalog] = []
        for cat_name, cat_slug, payment_model, sb_idx, has_window in CATALOGS:
            catalog = await get_or_create_catalog(
                session,
                company_id=company.id,
                sub_brand_id=sub_brands[sb_idx].id,
                created_by=sb_admin_users[sb_idx].id,
                approved_by=REEL48_ADMIN_USER_ID,
                name=cat_name,
                slug=cat_slug,
                payment_model=payment_model,
                has_buying_window=has_window,
            )
            catalogs.append(catalog)
        await session.commit()

        # -- Step 7: Link products to catalogs --
        print("\n[7/7] Catalog ↔ Product links")
        # North catalog gets North products (indices 0,1), South gets South (indices 2,3)
        catalog_product_map = [
            (catalogs[0], [products[0], products[1]]),  # North catalog
            (catalogs[1], [products[2], products[3]]),  # South catalog
        ]
        for catalog, cat_products in catalog_product_map:
            for order, product in enumerate(cat_products):
                await link_catalog_product(session, catalog, product, order)
        await session.commit()

    await engine.dispose()

    # -- Summary --
    print()
    print("=" * 60)
    print("  ACME Corp. Seed Data — Complete!")
    print("=" * 60)
    print()
    print(f"  Company:  {ACME_COMPANY['name']}")
    print(f"  ID:       {company.id}")
    print()
    print("  Sub-Brands:")
    for sb in sub_brands:
        default_tag = " (default)" if sb.is_default else ""
        print(f"    • {sb.name}{default_tag}  —  {sb.id}")
    print()
    print(f"  Password for ALL users: {DEFAULT_PASSWORD}")
    print()
    print(f"  {'Role':<20} {'Email':<45} {'Sub-Brand'}")
    print(f"  {'-'*20} {'-'*45} {'-'*15}")
    for i, (email, full_name, role, sb_idx, *_) in enumerate(USERS):
        sb_name = sub_brands[sb_idx].name if sb_idx is not None else "(all)"
        print(f"  {role:<20} {email:<45} {sb_name}")
    print()
    print(f"  Products: {len(products)} created")
    for p in products:
        print(f"    • {p.name} — ${p.unit_price} ({p.sku})")
    print()
    print(f"  Catalogs: {len(catalogs)} created")
    for c in catalogs:
        window = ""
        if c.buying_window_closes_at:
            window = f" (window closes {c.buying_window_closes_at.strftime('%Y-%m-%d')})"
        print(f"    • {c.name} — {c.payment_model}{window}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
