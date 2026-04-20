# Reel48+ Backend — CLAUDE.md

> ⚠ **SIMPLIFICATION IN PROGRESS** — see `~/.claude/plans/yes-please-write-the-memoized-karp.md`.
> Stale content has been removed: the `TenantBase` class, Module 3–9 table schemas, Stripe
> integration patterns, invoice lifecycle rules, order/bulk-order state machines, and 5-role
> authorization examples. Those systems are being torn down in Session A. This file will be
> rewritten authoritatively in Session D. Until then, do **not** reintroduce sub-brand columns,
> catalog/product/order/invoice models, `stripe` imports, or `sub_brand_admin`/`regional_manager`
> role references.


## Framework & Configuration

- **Python 3.11+** (modern syntax: `match`, `|` union, `type` aliases).
- **FastAPI** with async endpoints.
- **SQLAlchemy 2.0** (async sessions).
- **Alembic** for all migrations.
- **Pydantic v2** for schemas.
- **pytest** for testing.


## Local Development Setup

- Build backend: Hatchling (`pyproject.toml` `[tool.hatch.build.targets.wheel] packages = ["app"]`).
- Venv: `backend/.venv/`.
- Install: `cd backend && source .venv/bin/activate && pip install -e ".[dev]"`.
- Run: `uvicorn app.main:app --reload`.
- Env: copy `.env.example` to `.env`.
- structlog is configured at module level in `app/main.py`; tenant context is bound via
  `structlog.contextvars.bind_contextvars()` in the auth middleware.


## Project Structure (current reality — not aspirational)

The structure below reflects the state BEFORE Session A. After Session A, many files listed
here will be deleted. See the plan for the exact file list.

```
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py              # Pydantic BaseSettings
│   │   ├── database.py            # engine, session factory
│   │   ├── security.py            # JWT validation + JWKS cache
│   │   ├── dependencies.py        # get_tenant_context, get_db_session
│   │   ├── tenant.py              # TenantContext dataclass
│   │   ├── exceptions.py
│   │   └── rate_limit.py
│   ├── middleware/
│   │   ├── auth.py
│   │   ├── tenant.py              # sets PostgreSQL session variables for RLS
│   │   └── logging.py
│   ├── models/                    # See note below — most will be deleted in Session A
│   ├── schemas/                   # Pydantic request/response
│   ├── api/v1/                    # See note below — most will be deleted in Session A
│   └── services/                  # See note below — most will be deleted in Session A
├── migrations/versions/           # See note below — being consolidated
├── tests/
├── pyproject.toml
└── alembic.ini
```

**Do not treat the current file inventory as authoritative.** Consult the plan before
adding new files or assuming existing ones will survive.


## Authentication Middleware (stable)

Every authenticated request goes through `get_tenant_context` which:
1. Validates the Cognito JWT.
2. Extracts `custom:company_id` and `custom:role` claims.
3. Sets PostgreSQL session variables for RLS.
4. Returns a typed `TenantContext`.

### Session variables (company-only, target)
```python
# For non-reel48_admin users:
await db.execute(text(f"SET LOCAL app.current_company_id = '{context.company_id}'"))

# For reel48_admin (cross-company bypass):
await db.execute(text("SET LOCAL app.current_company_id = ''"))
```
`SET LOCAL` scopes to the current transaction — safe under connection pooling. `SET LOCAL`
does NOT support bind parameters; use f-string interpolation with validated UUIDs.

### `custom:sub_brand_id` Cognito attribute
Still exists in the user pool (AWS does not allow removing custom attributes). The backend
**ignores** it after Session A. Do not read this claim in new code.

### TenantContext (target shape)
```python
from dataclasses import dataclass
from uuid import UUID

@dataclass
class TenantContext:
    user_id: str
    company_id: UUID | None   # None for reel48_admin
    role: str                  # reel48_admin | company_admin | manager | employee

    @property
    def is_reel48_admin(self) -> bool:
        return self.role == "reel48_admin"

    @property
    def is_company_admin_or_above(self) -> bool:
        return self.role in ("reel48_admin", "company_admin")

    @property
    def is_manager_or_above(self) -> bool:
        return self.role in ("reel48_admin", "company_admin", "manager")
```

### Login & Token Refresh
Handled entirely client-side by AWS Amplify. There are NO backend login / refresh endpoints.
The backend only validates JWTs.

### Unauthenticated endpoints
After Session A, only two endpoints do not use `get_tenant_context`:
1. `POST /api/v1/auth/validate-org-code` (rate-limited)
2. `POST /api/v1/auth/register` (rate-limited)

(The Stripe webhook endpoint is being removed in Session A.)


## Endpoint Pattern (stable)

Route → Service → Model. Routes handle HTTP, services handle business logic, models handle
data access.

```python
router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    per_page: int = 20,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
):
    service = UserService(db)
    users, total = await service.list_users(context.company_id, page, per_page)
    return UserListResponse(data=users, meta={"page": page, "per_page": per_page, "total": total})
```

### Company-scoped endpoint guard
For tenant CRUD endpoints that operate within one company, add:
```python
def _require_company_id(context: TenantContext) -> UUID:
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id
```

### Platform admin endpoints
Live under `/api/v1/platform/{resource}/` and use `require_reel48_admin` as auth dependency.
May accept target `company_id` in the request body. Use `resolve_current_user_id()` to set
`approved_by` / `created_by` FKs.


## Pydantic Schema Conventions

- Separate `Create`, `Update`, `Response` schemas per resource.
- `Response` schemas use `model_config = ConfigDict(from_attributes=True)` to hydrate from
  SQLAlchemy models.
- Standard wrapper: `ApiResponse[T]` with `data`, `meta`, `errors` fields.


## Model Base Classes (target)

```python
class GlobalBase(Base):
    """For the companies table — has no tenant FK."""
    __abstract__ = True
    id = Column(UUID, primary_key=True, default=uuid4)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class CompanyBase(Base):
    """For every tenant-scoped table."""
    __abstract__ = True
    id = Column(UUID, primary_key=True, default=uuid4)
    company_id = Column(UUID, ForeignKey("companies.id"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

`TenantBase` (company_id + sub_brand_id) is being deleted in Session A. Do not import it.


## Database Session & RLS (stable)

```python
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Critical:** Always import `get_db_session` from `app.core.dependencies` (single canonical
path). FastAPI de-duplicates generator dependencies by object identity — two import paths
produce two separate sessions and one won't have the RLS session variables set.


## Deletion Strategy (unchanged)

- User-facing entities (users, companies): **soft delete** via `deleted_at` column. Service
  queries filter `deleted_at IS NULL`.
- Transient data (invite tokens, rate limit counters): **hard delete**.
- Org codes: **deactivation** (`is_active = false`), never deletion (users FK to them).


## External Service Integration Pattern (stable)

External services wrapped in a Service class + FastAPI dependency factory:
```python
class FooService:
    def __init__(self, client: Any):
        self._client = client

def get_foo_service() -> FooService:
    import some_sdk
    return FooService(some_sdk.Client(...))
```
boto3/SDK imports are lazy (inside the factory). Map SDK exceptions to `AppException`
subclasses inside the service. Test mocks override via `app.dependency_overrides`.

Surviving external services: `CognitoService`, `EmailService` (SES), `S3Service`.
**Removed in Session A:** `StripeService`.


## Error Handling (stable)

Custom exceptions (`AppException`, `NotFoundError`, `ForbiddenError`, `ConflictError`,
`RateLimitError`) are caught by a global handler in `main.py` that formats them into the
standard `{data: null, errors: [{code, message}]}` response.


## Rate Limiting (stable)

Redis-backed, factory-pattern FastAPI dependency. Graceful degradation: if Redis is
unavailable, requests pass through. Group-based (`rate_limit_auth` for `validate-org-code`
and `register`). IP-based via `request.client.host`.


## Logging (stable)

structlog with JSON renderer in production, console in debug. Bind tenant context in the
auth middleware via `bind_contextvars()` so every downstream log line carries `company_id`,
`user_id`, `role`.


## Testing (stable — see .claude/rules/testing.md)

- Dual sessions: `admin_db_session` (superuser, for seeding) and `db_session` (non-superuser,
  for isolation tests).
- Alembic migrations run via subprocess (asyncio conflict with pytest-asyncio).
- JWT tokens generated by `create_test_token()` with monkeypatched JWKS.
- External service mocks (`MockCognitoService`, `MockS3Service`, `MockEmailService`) via
  autouse fixtures and `app.dependency_overrides`. (`MockStripeService` is being removed.)
- Cross-company isolation test required for every module. Cross-sub-brand tests are NOT
  required (sub-brands are being removed).


## Table Schemas — TBD

Per-module table schema documentation is being rewritten. Session D will document the
final surviving tables:
- `companies`
- `users`
- `invites`
- `org_codes`
- `employee_profiles`
- `notifications`

Do not refer to schema documentation for removed tables (products, catalogs, orders,
bulk_orders, approvals, invoices, wishlists, sub_brands).
