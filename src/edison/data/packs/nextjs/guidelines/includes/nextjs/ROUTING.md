# Routing (App Router)

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Use App Router file-based routing under `app/`.
- Route handlers live in `app/api/**/route.ts` with named exports (`GET`, `POST`, ...).
- Prefer nouns in URLs; use `api/v1/<resource>` style segments when versioning is needed.
- Keep handlers thin: validate/auth at the boundary, delegate business logic to services.
- For route-handler details, see `packs/nextjs/guidelines/includes/nextjs/route-handlers.md`.
<!-- /section: patterns -->
