# API (Fastify)

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Keep business logic out of route handlers; call a service/module.
- Validate input at the boundary (Fastify schema / Zod / similar).
- Return consistent error shapes; prefer central error handler.

### Minimal illustrative pattern

```ts
import type { FastifyInstance } from 'fastify'

export async function registerRoutes(app: FastifyInstance) {
  app.get('/health', async () => {
    return { ok: true }
  })

  app.post('/v1/items', {
    schema: {
      body: {
        type: 'object',
        required: ['name'],
        properties: { name: { type: 'string', minLength: 1 } },
        additionalProperties: false,
      },
    },
  }, async (req, reply) => {
    const { name } = req.body as { name: string }

    const item = await app.diContainer.itemService.create({ name })
    return reply.code(201).send(item)
  })
}
```
<!-- /section: patterns -->
