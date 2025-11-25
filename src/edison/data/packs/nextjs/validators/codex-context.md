# Next.js Validation Context

{{include:.edison/packs/nextjs/guidelines/app-router.md}}
{{include:.edison/packs/nextjs/guidelines/route-handlers.md}}
{{include:.edison/packs/nextjs/guidelines/server-actions.md}}
{{include:.edison/packs/nextjs/guidelines/metadata.md}}
{{include:.edison/packs/nextjs/guidelines/caching.md}}

## Concrete Checks
- Use the App Router (`app/` directory) and Server Components by default.
- API endpoints implemented as `route.ts` handlers under `app/api/...`.
- Mutations use Server Actions with proper input validation on the server.
- Metadata configured via `generateMetadata` or static export where appropriate.
- Apply appropriate caching strategy (`dynamic`, `revalidate`) per route.

