---
globs: "**/storage/**,**/upload*,**/s3*,**/assets/**,**/media/**"
---

# Rule: S3 File Storage
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This rule activates when Claude Code is working on file upload/download   ║
# ║  functionality, S3 integration, or brand asset management. It ensures      ║
# ║  all file storage follows the tenant-isolated path structure.              ║
# ║                                                                            ║
# ║  WHY THIS RULE?                                                            ║
# ║                                                                            ║
# ║  Files stored in S3 must mirror the database's tenant isolation. If logos  ║
# ║  for Company A are stored at a path that Company B can guess, and          ║
# ║  pre-signed URLs aren't properly scoped, you have a data leak. This rule  ║
# ║  ensures the path structure encodes tenant and sub-brand boundaries.       ║
# ║                                                                            ║
# ║  EXTRA RULE (Recommended addition not in the original plan):               ║
# ║  This file also covers upload validation and virus scanning patterns       ║
# ║  that protect against malicious file uploads.                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Activates for: **/storage/**, **/upload**, **/s3**, **/assets/**, **/media/**

## S3 Path Structure (Mandatory)

All files MUST be stored under tenant-scoped paths:

```
s3://reel48-assets/
├── {company_id}/
│   ├── {sub_brand_slug}/
│   │   ├── logos/               # Sub-brand logos and brand assets
│   │   ├── products/            # Product images for this sub-brand's catalog
│   │   ├── catalog/             # Catalog configuration files
│   │   └── orders/              # Order-related documents
│   └── shared/                  # Company-wide assets (accessible by all sub-brands)
│       ├── logos/               # Corporate-level logos
│       └── templates/           # Shared templates
```

### Path Rules
- `company_id` is always a UUID (e.g., `a1b2c3d4-...`)
- `sub_brand_slug` is the URL-safe slug of the sub-brand name (e.g., `north-division`)
- NEVER store files at the bucket root
- NEVER store files outside the `{company_id}/` prefix
- Use the `shared/` directory for company-wide assets that all sub-brands can access

## Pre-signed URL Generation

### Downloads
```python
# WHY: Pre-signed URLs let the frontend download files directly from S3
# without the file passing through your backend server. This saves bandwidth
# and reduces latency. The 1-hour expiry limits the window of exposure if
# a URL leaks.

async def generate_download_url(
    company_id: UUID,
    sub_brand_slug: str,
    file_path: str,
) -> str:
    """Generate a pre-signed download URL (1-hour expiry)."""
    s3_key = f"{company_id}/{sub_brand_slug}/{file_path}"
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=3600,  # 1 hour
    )
    return url
```

### Uploads
```python
# WHY: Pre-signed upload URLs let the frontend upload directly to S3.
# The 15-minute expiry is shorter because upload URLs are more dangerous
# — they grant write access to your bucket.

async def generate_upload_url(
    company_id: UUID,
    sub_brand_slug: str,
    file_path: str,
    content_type: str,
) -> str:
    """Generate a pre-signed upload URL (15-minute expiry)."""
    s3_key = f"{company_id}/{sub_brand_slug}/{file_path}"
    url = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': BUCKET_NAME,
            'Key': s3_key,
            'ContentType': content_type,
        },
        ExpiresIn=900,  # 15 minutes
    )
    return url
```

## Upload Validation

### Allowed File Types
- **Logos/brand assets:** PNG, SVG, JPEG (max 5 MB)
- **Product images:** PNG, JPEG, WebP (max 10 MB)
- **Documents:** PDF (max 25 MB)
- Reject all other file types at the API level BEFORE generating upload URLs

### Validation Rules
1. Validate content type against the allowed list
2. Validate file extension matches content type
3. Set maximum file size per category
4. Sanitize filenames (strip special characters, replace spaces with hyphens)
5. Generate unique filenames to prevent overwrites:
   `{uuid}.{extension}` (e.g., `a1b2c3d4.png`)

## Access Control

### Tenant Scoping on Downloads
- Before generating a download URL, verify the requesting user's `company_id`
  matches the file's `{company_id}` path segment
- For sub-brand-scoped files, also verify the user's `sub_brand_id` matches
  (corporate admins bypass sub-brand checks)
- NEVER generate URLs for files outside the user's tenant scope

## CloudFront Integration
- Serve downloads through CloudFront for caching and reduced S3 costs
- Use CloudFront signed URLs (not S3 pre-signed URLs) for production
- Set cache headers appropriately:
  - Product images: `Cache-Control: public, max-age=86400` (24 hours)
  - Logos: `Cache-Control: public, max-age=604800` (7 days)
  - Documents: `Cache-Control: private, no-cache` (always fetch fresh)

## Implementation Lessons (S3 Storage Service)

# --- ADDED 2026-04-10 during S3 Storage Service Phases 1-4 ---
# Reason: Four-phase implementation revealed patterns and edge cases not
# anticipated by the original rule file.
# Impact: Future sessions working on file storage avoid these pitfalls.

### S3Service Follows External Service Integration Pattern
`S3Service` is injected via `get_s3_service()` dependency (same pattern as
CognitoService, StripeService, EmailService). boto3 import is lazy (inside the
factory function). `MockS3Service` in conftest.py replicates category validation
logic so tests accurately reflect real behavior.

### Tenant Validation on Download URLs
The download URL endpoint (`POST /api/v1/storage/download-url`) validates the
`s3_key` prefix against the user's `company_id` from TenantContext. The check
splits the key on `/` and compares the first segment. Sub-brand validation is
secondary — the primary security boundary is company-level isolation.

### JSONB Array Update Pattern for Product Images
Products store image URLs as a JSONB array (`image_urls`). SQLAlchemy doesn't detect
in-place JSONB mutations. The service copies the list, modifies it, and reassigns:
```python
new_list = list(product.image_urls)
new_list.append(s3_key)
product.image_urls = new_list
```
This triggers SQLAlchemy's change detection. Removing an image from `image_urls`
does NOT delete the file from S3 — orphaned files can be cleaned up by a future
background job.

### Profile Photo S3 Key Storage
Employee profiles store the S3 key (not the pre-signed URL) in `profile_photo_s3_key`.
The frontend resolves the key to a pre-signed URL at render time using the
`useDownloadUrl` hook or the `<S3Image>` component.

### Frontend Upload Pattern (Pre-Signed URL → Direct PUT)
The frontend uses a two-step pattern:
1. `POST /api/v1/storage/upload-url` to get a pre-signed URL + s3_key
2. `fetch(uploadUrl, { method: 'PUT', body: file })` to upload directly to S3

Client-side size validation runs BEFORE the API call to avoid unnecessary backend
requests. The `useFileUpload()` hook encapsulates the full flow. The API client's
`deepTransformKeys` converts request body keys to snake_case and response keys to
camelCase automatically — TypeScript types use camelCase field names.

### reel48_admin Rejected on Tenant Storage Endpoints
The storage endpoints use `get_tenant_context` and require `company_id` (which
`reel48_admin` lacks). The `_require_company_id` guard returns 403 with a message
directing to platform endpoints. Cross-company file access for platform admins
would need separate platform storage endpoints if needed in the future.

## Common Mistakes to Avoid
- ❌ Storing files at the bucket root (no tenant isolation)
- ❌ Using the same expiry time for upload and download URLs
- ❌ Not validating file types before generating upload URLs
- ❌ Exposing raw S3 URLs to the frontend (use pre-signed or CloudFront URLs)
- ❌ Allowing users to specify the S3 key directly (path traversal risk)
