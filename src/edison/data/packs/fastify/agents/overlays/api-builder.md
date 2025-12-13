# api-builder overlay for Fastify pack

<!-- extend: tools -->
- Fastify API lives in your API service; keep shared business logic in a dedicated service/core module instead of duplicating logic in a separate web app.
- Run your API service's lint/test commands (avoid hardcoded workspace filters).
- Fastify schema validation via JSON Schema or TypeBox.
<!-- /extend -->

<!-- extend: guidelines -->
### Critical Architecture
Business logic stays in the Fastify API service (and its shared service/core module). Any web-app route handlers should be thin proxies only.
<!-- /extend -->





