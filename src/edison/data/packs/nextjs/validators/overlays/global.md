# global overlay for Next.js pack

<!-- extend: tech-stack -->
## Next.js Validation Context

### Guidelines
{{include:packs/nextjs/guidelines/nextjs/app-router.md}}
{{include:packs/nextjs/guidelines/nextjs/route-handlers.md}}
{{include:packs/nextjs/guidelines/nextjs/server-actions.md}}
{{include:packs/nextjs/guidelines/nextjs/metadata.md}}
{{include:packs/nextjs/guidelines/nextjs/caching.md}}

### Concrete Checks
- Use the App Router (`app/` directory) and Server Components by default.
- API endpoints implemented as `route.ts` handlers under `app/api/...`.
- Mutations use Server Actions with proper input validation on the server.
- Metadata configured via `generateMetadata` or static export where appropriate.
- Apply appropriate caching strategy (`dynamic`, `revalidate`) per route.
<!-- /extend -->
