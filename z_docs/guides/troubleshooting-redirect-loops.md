# Troubleshooting: Next.js + Django Trailing Slash Redirect Loops

**Date:** 2026-02-01
**Context:** Next.js (Frontend) + Django (Backend Proxy)

## The Issue

Users experienced an infinite redirect loop (`ERR_TOO_MANY_REDIRECTS`) or 404 errors when accessing API endpoints proxied from Next.js to Django, specifically during authentication (`/api/v1/auth/naver/login/`) and content fetching (`/api/v1/content/preferred/`).

### Symptoms
- Browser console shows multiple 301 redirects switching between URLs with and without trailing slashes.
- `ERR_TOO_MANY_REDIRECTS` on login.
- `404 Not Found` for API endpoints that definitely exist.
- Browser caches `301 Moved Permanently` responses aggressively, causing the issue to persist even after server configuration changes ("Zombie Cache").

## Root Cause

The issue stems from a conflict between Next.js's default URL normalization and Django's strict slash enforcement.

1.  **Next.js Default Behavior:** By default, Next.js strips trailing slashes from URLs. A request to `/foo/` is normalized to `/foo`.
2.  **Django Default Behavior:** Django usually runs with `APPEND_SLASH=True`. If it receives a request for `/foo` (no slash) but the URL pattern defines `/foo/`, it returns a `301 Redirect` to `/foo/`.
3.  **The Loop:**
    - Next.js receives request `/api/v1/resource/`.
    - Next.js rewrite rule matches but forwards it as `/api/v1/resource` (stripping slash).
    - Django receives `/api/v1/resource`, sees it needs a slash, returns `301 -> /api/v1/resource/`.
    - Next.js passes this 301 to the browser.
    - Browser requests `/api/v1/resource/` again.
    - Loop continues.

4.  **The Cache Problem:** Once a browser receives a `301` redirect for a specific URL, it caches it *indefinitely* (or for a very long time). Even if you fix the server config, the browser skips the request and applies the cached redirect locally, often maintaining the loop.

## The Solution

### 1. Enable `trailingSlash: true` in Next.js

In `next.config.ts`, enable strict trailing slash handling. This tells Next.js to treat URLs with slashes as canonical and preserve them.

```typescript
const nextConfig: NextConfig = {
  trailingSlash: true, // CRITICAL FIX
  // ...
};
```

### 2. Configure Explicit Proxy Rewrites

Don't rely on catch-all rewrites that might be ambiguous about slashes. Define explicit rules for slash-preserving proxies if needed, or rely on `trailingSlash: true` to handle it globally.

In our case, we ensured the rewrites pass the path correctly.

```typescript
// next.config.ts
async rewrites() {
  return [
    {
      source: '/api/v1/:path*/', // Match trailing slash
      destination: `${coreUrl}/api/v1/:path*/`, // Preserve it
    },
    {
      source: '/api/v1/:path*', // Fallback
      destination: `${coreUrl}/api/v1/:path*`,
    },
  ];
}
```

### 3. Handle Browser Caching (For Users)

Since we cannot clear a user's browser cache remotely, we used a temporary "Cache Buster" technique during the fix verification:

- Appended `?_t=${Date.now()}` to critical URLs (like the login redirect).
- This makes the URL unique, forcing the browser to bypass its cache and hit the server, picking up the correct behavior.
- *Note: This was temporary code and removed after verification.*

## Prevention Checklist

1.  **Standardize URL Convention:** Decide early: **Always Slash** or **Never Slash**.
    - If using Django, **Always Slash** is the path of least resistance.
    - Ensure Next.js is set to `trailingSlash: true`.
    - Ensure Nginx (if used) preserves or enforces the same.
2.  **Avoid 301s in Development:** If possible, configure Django or redirects to use `302 Found` (Temporary) instead of `301 Moved Permanently` during development. 301s are the primary cause of "it's fixed but still broken" confusion.
3.  **Verify Proxy Rules:** When setting up `rewrites` or `proxy_pass`, explicitly test requests with and without trailing slashes to ensure they aren't being mutated unexpectedly.
