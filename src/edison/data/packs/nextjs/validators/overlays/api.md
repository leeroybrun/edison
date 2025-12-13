<!-- extend: composed-additions -->
# Next.js API Validation Context

{{include:packs/nextjs/guidelines/nextjs/route-handlers.md}}
{{include:packs/nextjs/guidelines/nextjs/app-router.md}}
{{include:packs/nextjs/guidelines/nextjs/caching.md}}

## Next.js API Checks
- Handlers live in `app/api/**/route.ts` using `NextRequest`/`NextResponse`; avoid legacy `pages/api` patterns.
- Validate inputs server-side (Zod) and return typed JSON with correct status codes; no client-only APIs in handlers.
- Declare caching/streaming explicitly (`dynamic`, `revalidate`, `cache` headers) to avoid serving stale authenticated data.
- Use `cookies()`/`headers()` from `next/headers` and built-in utilities instead of custom request parsing.
<!-- /extend -->
