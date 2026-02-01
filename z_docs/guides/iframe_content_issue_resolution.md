# Iframe Content Display Issue Resolution

**Date:** 2026-01-31
**Status:** Resolved in Development

## Problem Description
When clicking on a content item in the sidebar, the content detail view (which uses an `<iframe>` to display HTML content) showed a "localhost refused to connect" error.

## Root Causes
1.  **URL Encoding Issue**: Some filenames contained spaces (e.g., `.../asdfdsfd 2f90...html`). The URL generated in the frontend was not properly encoded, leading to malformed URLs that the browser or server could not handle correctly.
2.  **Cross-Origin Iframe Blocking**: The Next.js frontend runs on `localhost:3000`, while the Django backend (serving the media files) runs on `localhost:8000`. Django's default security middleware includes `XFrameOptionsMiddleware`, which sets the `X-Frame-Options` header to `DENY` or `SAMEORIGIN`. This blocked `localhost:3000` from embedding content from `localhost:8000`.

## Solution Implemented

### 1. Frontend (Client)
Updated `services/client/src/components/content/content-detail.tsx` to properly encode the URL before setting it as the iframe source.

```typescript
// Before
const absoluteUrl = backendUrl + url;

// After
const safeUrl = encodeURI(url);
const absoluteUrl = backendUrl + safeUrl;
```

### 2. Backend (Core - Development)
Updated `services/core/src/_changple/settings/development.py` to remove `XFrameOptionsMiddleware`. This allows iframes from any origin (including localhost:3000) in the development environment.

```python
# services/core/src/_changple/settings/development.py

# Allow iframes from localhost:3000 in development
if "django.middleware.clickjacking.XFrameOptionsMiddleware" in MIDDLEWARE:
    MIDDLEWARE.remove("django.middleware.clickjacking.XFrameOptionsMiddleware")
```

## Production Deployment Checklist

The fix applied to `development.py` **DOES NOT** apply to production automatically. You must ensure that content embedding works securely in the production environment.

1.  **Nginx / Reverse Proxy Configuration**:
    *   If production uses Nginx to serve both frontend and backend under the same domain (e.g., `https://example.com` and `https://example.com/api`), the default `SAMEORIGIN` policy might work.
    *   **Action**: Verify if Frontend and Backend share the exact same origin (scheme, host, and port) in production.

2.  **Production Django Settings (`production.py`)**:
    *   If Frontend and Backend are on different domains/subdomains (e.g., `app.example.com` and `api.example.com`), `SAMEORIGIN` will block the iframe.
    *   **Action**: You may need to configure `X_FRAME_OPTIONS = 'ALLOW-FROM https://your-frontend-domain.com'` (deprecated in some browsers) or preferably use **Content Security Policy (CSP)**.

3.  **Content Security Policy (CSP)**:
    *   The modern way to control iframe embedding is via the `Content-Security-Policy` header, specifically the `frame-ancestors` directive.
    *   **Action**: In `production.py` (or Nginx headers), ensure the backend sends:
        ```text
        Content-Security-Policy: frame-ancestors 'self' https://your-frontend-domain.com;
        ```
    *   If using `django-csp` or similar libraries, configure it accordingly.

4.  **Media Files Serving**:
    *   Ensure that wherever media files are served from in production (e.g., S3, Nginx serving static/media alias), the appropriate headers are set to allow embedding if they are served directly.
    *   If serving via Django (not recommended for high load but possible), the Django settings apply.
