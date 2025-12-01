# global overlay for Next.js pack

<!-- EXTEND: TechStack -->
## Next.js Validation Context

### Guidelines
{{include:.edison/_generated/guidelines/nextjs/app-router.md}}
{{include:.edison/_generated/guidelines/nextjs/route-handlers.md}}
{{include:.edison/_generated/guidelines/nextjs/server-actions.md}}
{{include:.edison/_generated/guidelines/nextjs/metadata.md}}
{{include:.edison/_generated/guidelines/nextjs/caching.md}}

### Concrete Checks
- Use the App Router (`app/` directory) and Server Components by default.
- API endpoints implemented as `route.ts` handlers under `app/api/...`.
- Mutations use Server Actions with proper input validation on the server.
- Metadata configured via `generateMetadata` or static export where appropriate.
- Apply appropriate caching strategy (`dynamic`, `revalidate`) per route.
<!-- /EXTEND -->
