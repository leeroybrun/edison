# Fastify API Validation Context

{{include:.edison/packs/fastify/guidelines/schema-validation.md}}
{{include:.edison/packs/fastify/guidelines/error-handling.md}}
{{include:.edison/packs/fastify/guidelines/auth.md}}

## Fastify-Specific Checks
- Attach JSON schemas for params, query, body, and responses on every route; keep response envelopes consistent.
- Use Fastify plugins/hooks for auth and error handling; avoid ad-hoc middleware that skips lifecycle hooks.
- Return errors via `reply.code(...).send(...)` and never leak stack traces; map validation failures to 400 with details.
- Keep handlers small—extract reusable schemas/plugins and register them with `fastify.register` for composability.
