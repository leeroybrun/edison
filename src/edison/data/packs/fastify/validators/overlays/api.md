<!-- EXTEND: composed-additions -->
# Fastify API Validation Context

{{include:.edison/_generated/guidelines/fastify/schema-validation.md}}
{{include:.edison/_generated/guidelines/fastify/error-handling.md}}
{{include:.edison/_generated/guidelines/fastify/auth.md}}

## Fastify-Specific Checks
- Attach JSON schemas for params, query, body, and responses on every route; keep response envelopes consistent.
- Use Fastify plugins/hooks for auth and error handling; avoid ad-hoc middleware that skips lifecycle hooks.
- Return errors via `reply.code(...).send(...)` and never leak stack traces; map validation failures to 400 with details.
- Keep handlers small—extract reusable schemas/plugins and register them with `fastify.register` for composability.
<!-- /EXTEND -->
