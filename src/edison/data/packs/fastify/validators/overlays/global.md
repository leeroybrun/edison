# global overlay for Fastify pack

<!-- EXTEND: TechStack -->
## Fastify API Validation Context

### Guidelines
{{include:.edison/_generated/guidelines/fastify/schema-validation.md}}
{{include:.edison/_generated/guidelines/fastify/error-handling.md}}
{{include:.edison/_generated/guidelines/fastify/auth.md}}

### Concrete Checks
- Validate request input (params, query, body) using a schema.
- Authenticate requests and enforce authorization for protected routes.
- Return consistent error responses; avoid leaking stack traces.
- Keep handlers small; extract reusable plugins and schemas.
<!-- /EXTEND -->
