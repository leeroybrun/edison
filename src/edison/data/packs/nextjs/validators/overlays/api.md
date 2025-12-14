<!-- extend: composed-additions -->
# Next.js API Validation Context

{{include-section:packs/nextjs/guidelines/includes/nextjs/route-handlers.md#patterns}}
{{include-section:packs/nextjs/guidelines/includes/nextjs/app-router.md#patterns}}
{{include-section:packs/nextjs/guidelines/includes/nextjs/caching.md#patterns}}

## Next.js API Checks
- Handlers live in `app/api/**/route.ts` using `NextRequest`/`NextResponse`; avoid legacy `pages/api` patterns.
- Validate inputs server-side (Zod) and return typed JSON with correct status codes; no client-only APIs in handlers.
- Declare caching/streaming explicitly (`dynamic`, `revalidate`, `cache` headers) to avoid serving stale authenticated data.
- Use `cookies()`/`headers()` from `next/headers` and built-in utilities instead of custom request parsing.
<!-- /extend -->
