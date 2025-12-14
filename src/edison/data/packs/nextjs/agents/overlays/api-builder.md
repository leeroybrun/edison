# api-builder overlay for Next.js pack

<!-- extend: tools -->
- Next.js App Router route handlers in `app/api/**/route.ts` (or your project's equivalent root).
- Use your project's authentication helper for route handlers (do not hardcode app-specific import paths).
- If your stack uses an ORM + schema validation, follow the active pack patterns (e.g., Prisma + Zod) and keep handlers thin.
- Run your project's lint/test commands for API routes (avoid hardcoded workspace filters).
<!-- /extend -->

<!-- extend: guidelines -->
### Key Patterns
- Export named functions: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- Accept `NextRequest` parameter
- Return `NextResponse` objects
- Use `requireAuth()` for authentication
- Use Zod for validation (recommended) or the project's configured validation library
- Use your project's data access layer consistently; do not hardcode ORM-specific helpers
- Keep handlers thin; if an upstream service exists, proxy rather than reimplementing business logic
- Reference: `packs/nextjs/guidelines/includes/nextjs/route-handlers.md`
<!-- /extend -->





