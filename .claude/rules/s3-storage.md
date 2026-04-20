---
globs: "**/storage/**,**/upload*,**/s3*,**/assets/**,**/media/**"
---

# Rule: S3 File Storage

> ⚠ **SIMPLIFICATION IN PROGRESS** — stripped as part of the refactor documented at
> `~/.claude/plans/yes-please-write-the-memoized-karp.md`. Previous content used
> `{company_id}/{sub_brand_slug}/...` paths. Sub-brands are being removed; all files
> now live under `{company_id}/...` directly. Do **not** reintroduce a sub-brand path
> segment on new S3 keys.

# Activates for: **/storage/**, **/upload**, **/s3**, **/assets/**, **/media/**

## S3 Path Structure (company-only)

All files MUST be stored under tenant-scoped paths:

```
s3://reel48-assets/
└── {company_id}/
    ├── logos/               # Company logos and brand assets
    ├── profiles/            # Employee profile photos
    └── (future categories as needed)
```

### Path Rules
- `company_id` is always a UUID.
- NEVER store files at the bucket root.
- NEVER store files outside the `{company_id}/` prefix.

Product/catalog/order categories are being removed in Session A (those features are
deferred to Shopify). Do not create new keys in those categories.

## Pre-signed URL Generation

### Downloads (1-hour expiry)
```python
async def generate_download_url(company_id: UUID, file_path: str) -> str:
    s3_key = f"{company_id}/{file_path}"
    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=3600,
    )
```

### Uploads (15-minute expiry)
```python
async def generate_upload_url(company_id: UUID, file_path: str, content_type: str) -> str:
    s3_key = f"{company_id}/{file_path}"
    return s3_client.generate_presigned_url(
        'put_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_key, 'ContentType': content_type},
        ExpiresIn=900,
    )
```

## Upload Validation

### Allowed File Types (surviving categories)
- **Logos:** PNG, SVG, JPEG (max 5 MB)
- **Profile photos:** PNG, JPEG (max 5 MB)
- Reject all other file types at the API level BEFORE generating upload URLs.

### Validation Rules
1. Validate content type against the allowed list.
2. Validate file extension matches content type.
3. Set maximum file size per category.
4. Sanitize filenames (strip special characters).
5. Generate unique filenames: `{uuid}.{extension}`.

## Access Control

### Tenant Scoping on Downloads
- Before generating a download URL, verify the requesting user's `company_id` matches the
  file's `{company_id}` path segment.
- NEVER generate URLs for files outside the user's tenant scope.

## CloudFront Integration
- Serve downloads through CloudFront for caching.
- Use CloudFront signed URLs (not S3 pre-signed URLs) for production.
- Cache headers:
  - Logos: `Cache-Control: public, max-age=604800` (7 days)
  - Profile photos: `Cache-Control: private, max-age=86400` (24 hours, private)

## S3Service Implementation Pattern (unchanged)
- Injected via `get_s3_service()` dependency.
- boto3 import is lazy (inside the factory function).
- `MockS3Service` in conftest.py replicates category validation logic.

## JSONB Array Update Pattern (retained for future use)
SQLAlchemy doesn't detect in-place JSONB mutations. Copy the list, modify, reassign:
```python
new_list = list(obj.image_urls)
new_list.append(s3_key)
obj.image_urls = new_list
```

## Frontend Upload Pattern (unchanged)
1. `POST /api/v1/storage/upload-url` to get a pre-signed URL + s3_key.
2. `fetch(uploadUrl, { method: 'PUT', body: file })` to upload directly to S3.
3. Save the returned `s3_key` in the relevant database column.

Client-side size validation runs BEFORE the API call. The `useFileUpload()` hook
encapsulates the full flow.

## Common Mistakes to Avoid
- ❌ Storing files at the bucket root.
- ❌ Reintroducing `{sub_brand_slug}` in S3 keys.
- ❌ Using the same expiry time for upload and download URLs.
- ❌ Not validating file types before generating upload URLs.
- ❌ Exposing raw S3 URLs to the frontend.
- ❌ Allowing users to specify the S3 key directly (path traversal risk).
