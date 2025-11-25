**CRITICAL ARCHITECTURE**: Business logic lives in the Fastify API (`apps/api` + `packages/api-core`). The Next.js app exposes thin proxy handlers that forward requests to Fastify. Do not implement business logic in Next.js handlers.

### Fastify route pattern (primary)

**File location**: `apps/dashboard/src/app/api/v1/dashboard/[resource]/route.ts`
