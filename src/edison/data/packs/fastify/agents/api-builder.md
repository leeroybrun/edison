# api-builder-fastify (Fastify API)

## Tools
- Fastify routes in `apps/api/src/routes/**` and shared logic in `packages/api-core`.
- Fastify schemas for validation and typed replies; Prisma client via API core.
- `pnpm test --filter api` / `pnpm lint --filter api` for API verification.

## Guidelines
- Business logic lives in Fastify; Next.js handlers should stay thin proxies. Keep mutations and validations in Fastify routes.
- Define `schema` with request/response types and status codes; use Zod or Fastify schema to enforce payloads.
- Return the project error envelope `{ error: string, details?: unknown }`; include correlation IDs and structured logs.
- Prefer shared helpers in `packages/api-core` to keep route files small and reusable.
- Example pattern:
```ts
server.route({
  method: 'GET',
  url: '/v1/dashboard/leads',
  schema: { querystring: QuerySchema, response: { 200: LeadsSchema } },
  handler: async (req, reply) => {
    const leads = await ctx.prisma.lead.findMany({
      where: req.query.status ? { status: req.query.status } : {},
      orderBy: { createdAt: 'desc' },
    })
    return reply.code(200).send({ data: leads })
  },
})
```
