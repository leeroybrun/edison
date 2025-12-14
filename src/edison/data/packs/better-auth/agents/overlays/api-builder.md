---
name: api-builder
pack: better-auth
overlay_type: extend
---

<!-- extend: guidelines -->

### Better Auth setup (pack)

- Prefer **server-side session validation** for protected resources.
- Keep middleware small; do not do provider calls in middleware.
- Keep redirects generic and configurable; avoid project-specific routes.

### Patterns

{{include-section:packs/better-auth/guidelines/includes/better-auth/session-management.md#patterns}}
{{include-section:packs/better-auth/guidelines/includes/better-auth/provider-configuration.md#patterns}}
{{include-section:packs/better-auth/guidelines/includes/better-auth/middleware-patterns.md#patterns}}
{{include-section:packs/better-auth/guidelines/includes/better-auth/client-setup-patterns.md#patterns}}
{{include-section:packs/better-auth/guidelines/includes/better-auth/security-best-practices.md#patterns}}

<!-- /extend -->
