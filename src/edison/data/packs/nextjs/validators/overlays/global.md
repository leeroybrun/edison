# global overlay for Next.js pack

<!-- extend: tech-stack -->
## Next.js Validation Context

### Guidelines
{{include-section:packs/nextjs/guidelines/includes/nextjs/app-router.md#patterns}}
{{include-section:packs/nextjs/guidelines/includes/nextjs/route-handlers.md#patterns}}
{{include-section:packs/nextjs/guidelines/includes/nextjs/server-actions.md#patterns}}
{{include-section:packs/nextjs/guidelines/includes/nextjs/metadata.md#patterns}}
{{include-section:packs/nextjs/guidelines/includes/nextjs/caching.md#patterns}}
{{include-section:packs/nextjs/guidelines/includes/nextjs/middleware.md#patterns}}

### Concrete Checks
- Use the App Router (`app/` directory) and Server Components by default.
- API endpoints implemented as `route.ts` handlers under `app/api/...`.
- Mutations use Server Actions with proper input validation on the server.
- Metadata configured via `generateMetadata` or static export where appropriate.
- Apply appropriate caching strategy (`dynamic`, `revalidate`) per route.
<!-- /extend -->
