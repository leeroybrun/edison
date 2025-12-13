# global overlay for Fastify pack

<!-- extend: tech-stack -->
## Fastify API Validation Context

### Guidelines
{{include:packs/fastify/guidelines/fastify/schema-validation.md}}
{{include:packs/fastify/guidelines/fastify/error-handling.md}}
{{include:packs/fastify/guidelines/fastify/auth.md}}

### Concrete Checks
- Validate request input (params, query, body) using a schema.
- Authenticate requests and enforce authorization for protected routes.
- Return consistent error responses; avoid leaking stack traces.
- Keep handlers small; extract reusable plugins and schemas.
<!-- /extend -->
