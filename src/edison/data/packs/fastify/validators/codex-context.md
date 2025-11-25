# Fastify API Validation Context

{{include:.edison/packs/fastify/guidelines/schema-validation.md}}
{{include:.edison/packs/fastify/guidelines/error-handling.md}}
{{include:.edison/packs/fastify/guidelines/auth.md}}

## Concrete Checks
- Validate request input (params, query, body) using a schema.
- Authenticate requests and enforce authorization for protected routes.
- Return consistent error responses; avoid leaking stack traces.
- Keep handlers small; extract reusable plugins and schemas.

