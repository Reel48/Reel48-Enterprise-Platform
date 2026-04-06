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

## Common Mistakes to Avoid
- ❌ Storing files at the bucket root (no tenant isolation)
- ❌ Using the same expiry time for upload and download URLs
- ❌ Not validating file types before generating upload URLs
- ❌ Exposing raw S3 URLs to the frontend (use pre-signed or CloudFront URLs)
- ❌ Allowing users to specify the S3 key directly (path traversal risk)
