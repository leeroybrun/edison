# global overlay for Fastify pack

<!-- extend: tech-stack -->
## Fastify API Validation Context

### Guidelines
{{include-section:packs/fastify/guidelines/includes/fastify/API.md#patterns}}
{{include-section:packs/fastify/guidelines/includes/fastify/schema-validation.md#patterns}}
{{include-section:packs/fastify/guidelines/includes/fastify/error-handling.md#patterns}}
{{include-section:packs/fastify/guidelines/includes/fastify/auth.md#patterns}}

### Concrete Checks
- Validate request input (params, query, body) using a schema.
- Authenticate requests and enforce authorization for protected routes.
- Return consistent error responses; avoid leaking stack traces.
- Keep handlers small; extract reusable plugins and schemas.
<!-- /extend -->
