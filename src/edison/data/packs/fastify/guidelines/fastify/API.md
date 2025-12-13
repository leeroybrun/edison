**CRITICAL ARCHITECTURE**: Business logic lives in the Fastify API service (and any shared service/core module). If a web app exposes proxy handlers that forward requests to Fastify, keep them thin—do not implement business logic in the proxy layer.

### Fastify route pattern (primary)

**File location**: `app/api/v1/<resource>/route.ts`
