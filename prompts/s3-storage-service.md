# S3 Storage Service — Phase-by-Phase Implementation Prompts
#
# Each phase below is a self-contained prompt designed to be pasted into a
# fresh Claude Code session. The session will read the CLAUDE.md harness files
# automatically — these prompts provide MODULE-SPECIFIC context that the
# harness doesn't cover.
#
# IMPORTANT: Run phases in order. Each phase depends on the prior phase's output.
#
# S3 STORAGE SERVICE OVERVIEW:
# The S3 Storage Service provides file upload and download capabilities for the
# Reel48+ platform. As an enterprise apparel management platform, real product
# images, brand logos, and employee profile photos are essential for a usable
# experience. Currently, product `image_urls` (JSONB) and profile
# `profile_photo_url` (Text) store placeholder values — this implementation
# makes them functional with real S3-backed file storage.
#
# This is NOT a new module — it is cross-cutting infrastructure that integrates
# with existing modules (Products from Module 3, Employee Profiles from Module 2,
# Sub-Brands from Module 1). No new database tables are created. The work is:
# 1. S3Service (AWS S3 client wrapper, dependency-injectable)
# 2. Storage API endpoints (pre-signed URL generation for upload/download)
# 3. Integration with existing endpoints (product image management, profile photos)
# 4. Comprehensive tests (functional, isolation, authorization, file validation)
#
# Key architectural points:
# - S3 path structure mirrors tenant isolation: `{company_id}/{sub_brand_slug}/...`
# - Frontend uploads directly to S3 via pre-signed URLs (not through the backend)
# - Frontend downloads via CloudFront or pre-signed URLs (never raw S3 URLs)
# - Pre-signed upload URLs expire after 15 minutes; download URLs after 1 hour
# - File type and size validation happens BEFORE generating upload URLs
# - S3Service follows the same External Service Integration Pattern as
#   CognitoService, StripeService, and EmailService (dependency-injectable, mockable)
#
# What ALREADY EXISTS (do not rebuild):
# - Product model (Module 3): `image_urls` JSONB column storing URL arrays
# - Employee Profile model (Module 2): `profile_photo_url` Text column
# - Sub-Brand model (Module 1): `slug` field used for S3 path construction
# - Company model (Module 1): `id` (UUID) used as S3 path root
# - All tenant isolation infrastructure (RLS, TenantContext, auth middleware)
# - External service integration pattern (CognitoService, StripeService, EmailService)
# - MockCognitoService, MockStripeService, MockEmailService in test conftest.py
# - 729 passing tests (632 backend + 97 frontend), all on `main` branch
#
# What this implementation BUILDS:
# - S3Service (boto3 S3 client wrapper, pre-signed URL generation)
# - `GET /api/v1/storage/upload-url` — Generate pre-signed upload URL
# - `GET /api/v1/storage/download-url` — Generate pre-signed download URL
# - `POST /api/v1/products/{product_id}/images` — Add image URL to product
# - `DELETE /api/v1/products/{product_id}/images/{index}` — Remove image from product
# - `POST /api/v1/profiles/me/photo` — Upload profile photo URL
# - `DELETE /api/v1/profiles/me/photo` — Remove profile photo
# - MockS3Service in conftest.py
# - Comprehensive tests (functional, isolation, authorization, validation)


---
---

# ===============================================================================
# PHASE 1: S3Service & Storage API Endpoints
# ===============================================================================

Build Phase 1 of the S3 Storage Service: the S3Service wrapper, FastAPI dependency,
storage API endpoints for pre-signed URL generation, and test infrastructure updates.

## Context

We are building the S3 Storage Service for the Reel48+ enterprise apparel platform.
All 9 modules are complete:
- Module 1: Auth, Companies, Sub-Brands, Users, Org Codes, Invites (migration `001`)
- Module 2: Employee Profiles (migration `002`)
- Module 3: Products, Catalogs, Catalog-Products (migration `003`)
- Module 4: Orders, Order Line Items (migration `004`)
- Module 5: Bulk Orders, Bulk Order Items (migration `005`)
- Module 6: Approval Requests, Approval Rules (migration `006`)
- Module 7: Invoices (migration `007`)
- Module 8: Analytics (no migration — read-only queries)
- Module 9: Notifications, Wishlists (migration `009`)

The current test suite has 729 passing tests (632 backend + 97 frontend).
The branch is `main`. Create a new branch `feature/s3-storage-service-phase1` from
`main` before starting.

## What to Build

### 1. S3Service (`backend/app/services/s3_service.py`)

Create an S3Service class following the External Service Integration Pattern established
by CognitoService, StripeService, and EmailService. Key requirements:

```python
class S3Service:
    """
    Wraps boto3 S3 client for pre-signed URL generation and file management.
    Follows the same dependency injection pattern as CognitoService/StripeService.
    """
    def __init__(self, client: Any, bucket_name: str, cloudfront_domain: str | None = None):
        self._client = client  # boto3 S3 client
        self._bucket_name = bucket_name
        self._cloudfront_domain = cloudfront_domain

    def generate_upload_url(
        self,
        company_id: UUID,
        sub_brand_slug: str,
        category: str,         # "logos", "products", "catalog", "profiles"
        content_type: str,
        file_extension: str,
    ) -> tuple[str, str]:
        """
        Generate a pre-signed PUT URL for direct browser upload.
        Returns: (upload_url, s3_key)
        - Validates content_type against allowed types for the category
        - Generates a unique filename: {uuid}.{extension}
        - Builds the S3 key: {company_id}/{sub_brand_slug}/{category}/{uuid}.{ext}
        - Pre-signed URL expires in 15 minutes
        """

    def generate_download_url(
        self,
        s3_key: str,
    ) -> str:
        """
        Generate a pre-signed GET URL for file download.
        - Pre-signed URL expires in 1 hour (3600 seconds)
        - If cloudfront_domain is configured, generate a CloudFront URL instead
        """

    def generate_shared_download_url(
        self,
        company_id: UUID,
        file_path: str,
    ) -> str:
        """
        Generate download URL for company-wide shared assets.
        S3 key: {company_id}/shared/{file_path}
        """
```

**File type validation rules (enforce in `generate_upload_url`):**
| Category | Allowed Types | Max Size | Allowed Extensions |
|----------|--------------|----------|--------------------|
| `logos` | `image/png`, `image/svg+xml`, `image/jpeg` | 5 MB | `.png`, `.svg`, `.jpg`, `.jpeg` |
| `products` | `image/png`, `image/jpeg`, `image/webp` | 10 MB | `.png`, `.jpg`, `.jpeg`, `.webp` |
| `catalog` | `application/pdf` | 25 MB | `.pdf` |
| `profiles` | `image/png`, `image/jpeg` | 5 MB | `.png`, `.jpg`, `.jpeg` |

Raise `ValidationError` (422) if content_type or extension doesn't match the category.
Note: file SIZE validation cannot be enforced server-side for pre-signed uploads — it
must be enforced client-side. The service validates type/extension only.

**Unique filename generation:**
Use `{uuid4()}.{extension}` to prevent filename collisions and path traversal. Never
use user-provided filenames in the S3 key.

### 2. S3Service Dependency Factory (`backend/app/core/dependencies.py`)

Add `get_s3_service()` to the existing dependencies file:

```python
def get_s3_service() -> S3Service:
    """FastAPI dependency — creates boto3 S3 client + returns S3Service."""
    import boto3  # Lazy import (same pattern as CognitoService)
    client = boto3.client("s3", region_name=settings.AWS_REGION)
    return S3Service(
        client=client,
        bucket_name=settings.S3_BUCKET_NAME,
        cloudfront_domain=settings.CLOUDFRONT_DOMAIN,
    )
```

### 3. Settings Updates (`backend/app/core/config.py`)

Add the following settings to the existing `Settings` class:

```python
S3_BUCKET_NAME: str = "reel48-assets"
CLOUDFRONT_DOMAIN: str | None = None  # Optional — if set, download URLs use CloudFront
AWS_REGION: str = "us-east-1"  # May already exist for Cognito/SES
```

### 4. Storage API Endpoints (`backend/app/api/v1/storage.py`)

Create a new route module for storage operations:

**`POST /api/v1/storage/upload-url`** — Generate pre-signed upload URL
- Requires authentication (`get_tenant_context`)
- Request body:
  ```json
  {
    "category": "products",        // "logos" | "products" | "catalog" | "profiles"
    "content_type": "image/png",
    "file_extension": ".png"
  }
  ```
- Response:
  ```json
  {
    "data": {
      "upload_url": "https://s3.amazonaws.com/...",
      "s3_key": "company-uuid/brand-slug/products/file-uuid.png",
      "expires_in": 900
    },
    "meta": {},
    "errors": []
  }
  ```
- Sub-brand slug resolution: Look up the user's `sub_brand_id` from TenantContext,
  query the `sub_brands` table for the slug. For corporate_admin (sub_brand_id=None),
  use "shared" as the path segment.
- Role requirements: All authenticated users can request upload URLs (employees
  upload profile photos; admins upload product images and logos).

**`POST /api/v1/storage/download-url`** — Generate pre-signed download URL
- Requires authentication (`get_tenant_context`)
- Request body:
  ```json
  {
    "s3_key": "company-uuid/brand-slug/products/file-uuid.png"
  }
  ```
- Response:
  ```json
  {
    "data": {
      "download_url": "https://s3.amazonaws.com/...",
      "expires_in": 3600
    },
    "meta": {},
    "errors": []
  }
  ```
- **CRITICAL tenant validation:** Before generating the URL, verify the `s3_key`
  starts with the user's `company_id`. A user from Company A must NOT be able to
  generate download URLs for Company B's files. Extract the company_id from the
  key's first path segment and compare against `context.company_id`. For
  `reel48_admin` (company_id=None), skip the company check (platform admins can
  access any company's files). Additionally, for non-corporate users, verify the
  sub_brand_slug segment matches (or the path uses "shared").

### 5. Pydantic Schemas (`backend/app/schemas/storage.py`)

```python
from pydantic import BaseModel, field_validator
from typing import Literal

class UploadUrlRequest(BaseModel):
    category: Literal["logos", "products", "catalog", "profiles"]
    content_type: str
    file_extension: str

    @field_validator("file_extension")
    @classmethod
    def normalize_extension(cls, v: str) -> str:
        """Ensure extension starts with a dot and is lowercase."""
        v = v.lower().strip()
        if not v.startswith("."):
            v = f".{v}"
        return v

class UploadUrlResponse(BaseModel):
    upload_url: str
    s3_key: str
    expires_in: int

class DownloadUrlRequest(BaseModel):
    s3_key: str

class DownloadUrlResponse(BaseModel):
    download_url: str
    expires_in: int
```

### 6. Router Registration (`backend/app/api/v1/router.py`)

Add the storage router to the existing v1 router aggregation:
```python
from app.api.v1.storage import router as storage_router
api_v1_router.include_router(storage_router)
```

### 7. Test Infrastructure Updates (`backend/tests/conftest.py`)

**MockS3Service:** Create a mock following the established pattern:

```python
class MockS3Service:
    """Mock S3 service for testing. Records calls, does not hit AWS."""
    def __init__(self):
        self.generated_upload_urls: list[dict] = []
        self.generated_download_urls: list[dict] = []

    def generate_upload_url(
        self, company_id, sub_brand_slug, category, content_type, file_extension
    ) -> tuple[str, str]:
        s3_key = f"{company_id}/{sub_brand_slug}/{category}/test-{uuid4()}{file_extension}"
        url = f"https://s3.amazonaws.com/reel48-assets/{s3_key}?presigned=true"
        self.generated_upload_urls.append({
            "company_id": str(company_id),
            "sub_brand_slug": sub_brand_slug,
            "category": category,
            "content_type": content_type,
            "s3_key": s3_key,
        })
        return url, s3_key

    def generate_download_url(self, s3_key: str) -> str:
        url = f"https://s3.amazonaws.com/reel48-assets/{s3_key}?presigned=true"
        self.generated_download_urls.append({"s3_key": s3_key})
        return url

    def generate_shared_download_url(self, company_id, file_path) -> str:
        s3_key = f"{company_id}/shared/{file_path}"
        return f"https://s3.amazonaws.com/reel48-assets/{s3_key}?presigned=true"
```

Add an autouse fixture:
```python
@pytest.fixture(autouse=True)
def mock_s3(app) -> MockS3Service:
    mock = MockS3Service()
    app.dependency_overrides[get_s3_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_s3_service, None)
```

### 8. Tests (`backend/tests/test_storage.py`)

Write comprehensive tests covering:

**Functional tests:**
- Generate upload URL with valid category + content_type returns 200 with URL and s3_key
- Generated s3_key follows the pattern `{company_id}/{sub_brand_slug}/{category}/{uuid}.{ext}`
- Generate download URL with a valid s3_key returns 200 with URL
- Invalid content_type for category returns 422 (e.g., `image/gif` for `products`)
- Invalid file_extension for category returns 422
- Missing required fields returns 422
- Extension normalization works (no dot prefix, uppercase → lowercase)
- Corporate admin upload URL uses "shared" path segment (sub_brand_id=None)

**Isolation tests:**
- Company B user cannot generate download URL for Company A's s3_key (returns 403)
- Sub-Brand A2 user cannot generate download URL for Sub-Brand A1's path (returns 403)
- Corporate admin CAN generate download URLs for any sub-brand within their company
- `reel48_admin` CAN generate download URLs for any company's files

**Authorization tests:**
- Unauthenticated requests return 401
- All authenticated roles (employee through reel48_admin) can generate upload URLs
- All authenticated roles can generate download URLs (within their tenant scope)

## Implementation Notes

- Follow the established endpoint pattern: route → service, with `ApiResponse[T]` wrapper
- Use `_require_company_id(context)` guard for upload URL generation (reel48_admin has
  no company_id, so they should use platform endpoints or the company_id must be
  provided differently — for Phase 1, reject reel48_admin on tenant storage endpoints
  with "Use platform endpoints")
- The storage endpoints are tenant-scoped, NOT platform endpoints. reel48_admin
  file access can be added as platform endpoints in a future phase if needed.
- Add `"storage"` to the tags list in the router

## Harness Updates Required

After implementation, update the following harness files:
- **`backend/CLAUDE.md`:** Add S3Service to the project structure and External Service
  Integration Pattern section. Add storage.py to the API routes listing.
- **`docs/harness-changelog.md`:** Log this phase's changes.


---
---

# ===============================================================================
# PHASE 2: Product Image Management Endpoints
# ===============================================================================

Build Phase 2: Integrate S3 storage with the existing Product model and endpoints
for managing product images.

## Context

Phase 1 is complete: S3Service, storage API endpoints, and MockS3Service are in place.
The Product model already has an `image_urls` JSONB column (default `[]`). This phase
adds endpoints to manage that array through the S3 storage pipeline.

Create a new branch `feature/s3-storage-service-phase2` from `main` (or from the
Phase 1 branch if not yet merged).

## What to Build

### 1. New Product Image Endpoints (`backend/app/api/v1/products.py`)

Add to the existing products router:

**`POST /api/v1/products/{product_id}/images`** — Add image to product
- Requires `is_admin` role (only admins manage product images)
- Request body:
  ```json
  {
    "s3_key": "company-uuid/brand-slug/products/file-uuid.png"
  }
  ```
- Validates:
  - Product exists and is in the user's tenant scope
  - Product is in `draft` status (images can only be managed on drafts, same as other edits)
  - s3_key starts with the correct `company_id` (tenant validation)
  - s3_key is in the `products` category path
  - `image_urls` array doesn't exceed 10 items (reasonable limit)
- Appends the s3_key to `product.image_urls` JSONB array
- Returns the updated product

**`DELETE /api/v1/products/{product_id}/images/{index}`** — Remove image from product
- Requires `is_admin` role
- `index` is the 0-based position in the `image_urls` array
- Validates:
  - Product exists and is in the user's tenant scope
  - Product is in `draft` status
  - Index is within bounds
- Removes the URL at the specified index from `image_urls`
- Returns the updated product
- Does NOT delete the file from S3 (orphaned files can be cleaned up by a future
  background job — keep it simple for now)

### 2. Product Service Updates (`backend/app/services/product_service.py`)

Add methods to ProductService:

```python
async def add_product_image(
    self, product_id: UUID, s3_key: str, company_id: UUID, sub_brand_id: UUID | None
) -> Product:
    """Add an image URL to a product's image_urls array."""

async def remove_product_image(
    self, product_id: UUID, index: int, company_id: UUID, sub_brand_id: UUID | None
) -> Product:
    """Remove an image URL from a product's image_urls array by index."""
```

**JSONB array update pattern:** SQLAlchemy doesn't detect in-place JSONB mutations.
Use one of these approaches:
- Copy the list, modify, reassign: `urls = list(product.image_urls); urls.append(key); product.image_urls = urls`
- Or use `flag_modified(product, "image_urls")` after mutation

### 3. Tests (`backend/tests/test_products.py` — add to existing file)

Add tests to the existing product test file:

**Functional tests:**
- Add image to draft product returns 200 with updated image_urls
- Add image to non-draft product returns 403
- Add 11th image (exceeding limit) returns 422
- Remove image by valid index returns 200
- Remove image with out-of-bounds index returns 422
- Removed image is no longer in the product's image_urls

**Isolation tests:**
- Company B admin cannot add images to Company A's product (404)
- s3_key with wrong company_id prefix is rejected (403)

**Authorization tests:**
- Employee cannot add/remove product images (403)
- Sub-brand admin can add images to their sub-brand's products
- Corporate admin can add images to any sub-brand's products in their company

## Harness Updates Required

After implementation, update:
- **`backend/CLAUDE.md`:** Note that product image management endpoints exist.
- **`docs/harness-changelog.md`:** Log this phase's changes.


---
---

# ===============================================================================
# PHASE 3: Profile Photo Management
# ===============================================================================

Build Phase 3: Integrate S3 storage with the existing Employee Profile model for
profile photo upload and removal.

## Context

Phases 1-2 are complete: S3Service, storage endpoints, and product image management
are in place. The EmployeeProfile model already has a `profile_photo_url` Text column
(default NULL). This phase adds endpoints for employees to manage their own profile photo.

Create a new branch `feature/s3-storage-service-phase3` from `main` (or from the
Phase 2 branch if not yet merged).

## What to Build

### 1. Profile Photo Endpoints (`backend/app/api/v1/employee_profiles.py`)

Add to the existing employee profiles router:

**`POST /api/v1/profiles/me/photo`** — Set profile photo URL
- Requires authentication (any role — employees manage their own photo)
- Request body:
  ```json
  {
    "s3_key": "company-uuid/brand-slug/profiles/file-uuid.png"
  }
  ```
- Validates:
  - s3_key starts with the correct `company_id`
  - s3_key is in the `profiles` category path
  - Profile exists for the current user (if not, return 404 with guidance to create
    profile first via `PUT /profiles/me`)
- Sets `profile.profile_photo_url = s3_key`
- Returns the updated profile

**`DELETE /api/v1/profiles/me/photo`** — Remove profile photo
- Requires authentication (any role)
- Sets `profile.profile_photo_url = None`
- Returns the updated profile
- Does NOT delete the file from S3

### 2. Profile Service Updates (`backend/app/services/employee_profile_service.py`)

Add methods:

```python
async def set_profile_photo(
    self, user_id: UUID, s3_key: str
) -> EmployeeProfile:
    """Set the profile photo URL for the user's profile."""

async def remove_profile_photo(
    self, user_id: UUID
) -> EmployeeProfile:
    """Remove the profile photo URL from the user's profile."""
```

### 3. Tests (`backend/tests/test_employee_profiles.py` — add to existing file)

**Functional tests:**
- Set profile photo returns 200 with updated profile_photo_url
- Remove profile photo returns 200 with profile_photo_url = null
- Set photo when no profile exists returns 404
- Set photo overwrites previous photo URL

**Isolation tests:**
- s3_key with wrong company_id prefix is rejected (403)

**Authorization tests:**
- Any authenticated role can set/remove their own profile photo
- Cannot set another user's profile photo (endpoint is `/me` scoped)

## Harness Updates Required

After implementation, update:
- **`docs/harness-changelog.md`:** Log this phase's changes.


---
---

# ===============================================================================
# PHASE 4: Frontend Integration & Harness Updates
# ===============================================================================

Build Phase 4: Frontend utilities for S3 upload/download and the end-of-implementation
harness review.

## Context

Phases 1-3 are complete: S3Service, storage endpoints, product image management, and
profile photo management are all in place on the backend. This phase adds the frontend
utilities and components needed to actually use the storage service, plus the mandatory
harness review.

Create a new branch `feature/s3-storage-service-phase4` from `main` (or from the
Phase 3 branch if not yet merged).

## What to Build

### 1. Storage API Client Hooks (`frontend/src/hooks/useStorage.ts`)

Create React Query hooks for storage operations:

```typescript
'use client';

import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface UploadUrlRequest {
  category: 'logos' | 'products' | 'catalog' | 'profiles';
  content_type: string;
  file_extension: string;
}

interface UploadUrlResponse {
  upload_url: string;
  s3_key: string;
  expires_in: number;
}

interface DownloadUrlResponse {
  download_url: string;
  expires_in: number;
}

/**
 * Request a pre-signed upload URL, then PUT the file directly to S3.
 * Returns the s3_key on success (to store in the database).
 */
export function useFileUpload() {
  return useMutation({
    mutationFn: async ({
      file,
      category,
    }: {
      file: File;
      category: UploadUrlRequest['category'];
    }) => {
      // 1. Client-side file size validation
      const maxSizes: Record<string, number> = {
        logos: 5 * 1024 * 1024,
        products: 10 * 1024 * 1024,
        catalog: 25 * 1024 * 1024,
        profiles: 5 * 1024 * 1024,
      };
      if (file.size > maxSizes[category]) {
        throw new Error(`File exceeds maximum size for ${category}`);
      }

      // 2. Get pre-signed URL from backend
      const extension = '.' + file.name.split('.').pop()?.toLowerCase();
      const { data } = await apiClient.post<{ data: UploadUrlResponse }>(
        '/api/v1/storage/upload-url',
        { category, content_type: file.type, file_extension: extension }
      );

      // 3. Upload directly to S3
      await fetch(data.data.upload_url, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': file.type },
      });

      return data.data.s3_key;
    },
  });
}

/**
 * Get a pre-signed download URL for an s3_key.
 */
export function useDownloadUrl() {
  return useMutation({
    mutationFn: async (s3Key: string) => {
      const { data } = await apiClient.post<{ data: DownloadUrlResponse }>(
        '/api/v1/storage/download-url',
        { s3_key: s3Key }
      );
      return data.data.download_url;
    },
  });
}
```

### 2. TypeScript Types (`frontend/src/types/storage.ts`)

```typescript
export interface UploadUrlRequest {
  category: 'logos' | 'products' | 'catalog' | 'profiles';
  content_type: string;
  file_extension: string;
}

export interface UploadUrlResponse {
  upload_url: string;
  s3_key: string;
  expires_in: number;
}

export interface DownloadUrlResponse {
  download_url: string;
  expires_in: number;
}

export type StorageCategory = UploadUrlRequest['category'];
```

### 3. Image Display Component (`frontend/src/components/ui/S3Image.tsx`)

Create the FIRST component in the `src/components/ui/` directory — a reusable
S3-backed image component:

```typescript
'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { Loading } from '@carbon/react';
import { useDownloadUrl } from '@/hooks/useStorage';

interface S3ImageProps {
  s3Key: string | null;
  alt: string;
  width: number;
  height: number;
  fallback?: React.ReactNode;
  className?: string;
}

/**
 * Displays an image stored in S3 by resolving a pre-signed download URL.
 * Shows a loading state while the URL is being fetched, and a fallback
 * if s3Key is null or the fetch fails.
 */
export function S3Image({ s3Key, alt, width, height, fallback, className }: S3ImageProps) {
  // Implementation: use useDownloadUrl mutation to resolve the s3_key
  // to a pre-signed URL, then render with next/image.
  // Cache resolved URLs in component state to avoid re-fetching on re-renders.
  // Show Carbon Loading spinner while resolving.
  // Show fallback (or a default placeholder) if s3Key is null.
}
```

This component handles the common pattern of "I have an s3_key in the database, show
the image." It follows Carbon design system conventions (Loading component for loading
state) and uses `next/image` for optimization.

### 4. Frontend Tests

Add tests for the new hooks and component:

**`frontend/src/__tests__/storage.test.tsx`:**
- `useFileUpload` calls the upload-url endpoint and PUTs to S3
- `useFileUpload` rejects files exceeding size limits before API call
- `useDownloadUrl` calls the download-url endpoint and returns the URL
- `S3Image` shows loading state while resolving URL
- `S3Image` renders image after URL resolves
- `S3Image` shows fallback when s3Key is null

Mock the API client and `fetch` for S3 upload testing.

### 5. Mandatory Harness Review & Updates

This is the final phase. Perform the End-of-Session Self-Audit and update all
relevant harness files:

**Root CLAUDE.md:**
- No changes expected (S3 path structure and pre-signed URL patterns are already documented)

**Backend CLAUDE.md:**
- Add `s3_service.py` to the services listing in Project Structure
- Add `storage.py` to the API routes listing
- Add S3Service to the External Service Integration Pattern section (alongside
  CognitoService, StripeService, EmailService)
- Add `S3_BUCKET_NAME`, `CLOUDFRONT_DOMAIN` to any settings reference

**Frontend CLAUDE.md:**
- Add `useStorage.ts` to the hooks listing
- Add `storage.ts` to the types listing
- Add `S3Image.tsx` to the components/ui listing
- Note the S3 upload pattern (pre-signed URL → direct PUT to S3)

**`.claude/rules/s3-storage.md`:**
- Add any implementation lessons learned (similar to the Module 7 Stripe lessons)
- Add the tenant validation pattern for download URLs
- Add the JSONB array update pattern for product images

**`docs/harness-changelog.md`:**
- Add a comprehensive entry covering all 4 phases
- Note: no database migration was needed (no new tables)
- Note: S3Service follows the established External Service Integration Pattern
- Note: S3Image is the first component in `src/components/ui/`

## Verification Checklist

Before committing the final phase:
- [ ] All existing tests still pass (729+ backend, 97+ frontend)
- [ ] New storage tests pass
- [ ] New product image tests pass
- [ ] New profile photo tests pass
- [ ] New frontend tests pass
- [ ] TypeScript compiles without errors (`npx tsc --noEmit`)
- [ ] ESLint passes (`npx next lint`)
- [ ] Harness files are updated
- [ ] Changelog entry is committed
