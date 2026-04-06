# Prompt Template: CRUD Endpoint
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS?                                                             ║
# ║                                                                            ║
# ║  This is a REUSABLE PROMPT TEMPLATE. When you need Claude Code to build    ║
# ║  a new CRUD endpoint, copy this template, fill in the blanks, and submit   ║
# ║  it. The template ensures you don't forget any critical details (like      ║
# ║  tenant isolation or role checks) and produces consistent results.         ║
# ║                                                                            ║
# ║  WHY A PROMPT LIBRARY?                                                     ║
# ║                                                                            ║
# ║  Prompts are like recipes. A good recipe produces consistent results       ║
# ║  every time. Without templates, each developer writes slightly different   ║
# ║  prompts, getting inconsistent output. The prompt library captures what    ║
# ║  works and makes it repeatable. Over time, refine these templates based    ║
# ║  on what produces the best results.                                        ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

## Template

```
Create a complete CRUD API for the {ENTITY_NAME} resource.

### Entity Details
- Table name: {table_name}
- Key fields: {list of fields with types}
- Relationships: {foreign keys and related entities}

### Requirements
1. SQLAlchemy model inheriting from TenantBase (includes company_id, sub_brand_id, id, timestamps)
2. Alembic migration with RLS policies (company isolation + sub-brand scoping)
3. Pydantic schemas: {Entity}Create, {Entity}Update, {Entity}Response
4. FastAPI endpoints:
   - GET /api/v1/{entities} — list with pagination (filtered by tenant context)
   - GET /api/v1/{entities}/{id} — get single
   - POST /api/v1/{entities} — create (requires {required_role} role)
   - PATCH /api/v1/{entities}/{id} — partial update
   - DELETE /api/v1/{entities}/{id} — soft delete or hard delete: {specify}
5. Service layer with business logic
6. Tests:
   - Functional: create, read, update, delete operations
   - Isolation: cross-company access blocked, cross-sub-brand access blocked
   - Authorization: role restrictions enforced
   - Corporate admin can see all sub-brands

### Acceptance Criteria
- [ ] All endpoints use TenantContext from JWT (never accept company_id as parameter)
- [ ] RLS policies created in the same migration as the table
- [ ] Defense-in-depth: application-layer filtering AND RLS
- [ ] Standard response format: { data, meta, errors }
- [ ] All tests pass, including isolation tests
- [ ] Pagination on the list endpoint with meta.total count

### Existing Code Context
- Auth middleware: app/middleware/auth.py
- Base model: app/models/base.py
- Example endpoint to follow: app/api/v1/{existing_endpoint}.py
```

## Example: Filled-In for Products

```
Create a complete CRUD API for the Product resource.

### Entity Details
- Table name: products
- Key fields: name (str, required), sku (str, unique per company), description (text, optional), unit_price (decimal 10,2), sizes (JSON array), decoration_options (JSON array), image_urls (JSON array)
- Relationships: FK to companies, FK to sub_brands. Products belong to a sub-brand's catalog.

### Requirements
1. SQLAlchemy model inheriting from TenantBase
2. Alembic migration with RLS policies
3. Pydantic schemas: ProductCreate, ProductUpdate, ProductResponse
4. FastAPI endpoints:
   - GET /api/v1/products — list with pagination, filterable by sub_brand_id for corporate admins
   - GET /api/v1/products/{id} — get single
   - POST /api/v1/products — create (requires sub_brand_admin or corporate_admin)
   - PATCH /api/v1/products/{id} — partial update
   - DELETE /api/v1/products/{id} — soft delete (set is_active=false)
5. Service layer with SKU uniqueness validation per company
6. Tests including cross-tenant isolation and role authorization

### Acceptance Criteria
- Same as template above, plus:
- [ ] SKU is unique within a company (not globally)
- [ ] Corporate admin can create products for any sub-brand
- [ ] Sub-brand admin can only create products for their own sub-brand

### Existing Code Context
- Auth middleware: app/middleware/auth.py
- Base model: app/models/base.py
```
