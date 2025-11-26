# api-builder-fastify (Fastify API)

## Tools
- Fastify API lives in `apps/api` with shared helpers in `packages/api-core`; use these packages instead of duplicating handlers in Next.js.
- Use `pnpm --filter api test` and `pnpm --filter api lint` for Fastify-specific validation.
- Fastify schema validation via JSON Schema or TypeBox.

## Guidelines

### Critical Architecture
Business logic stays in the Fastify API (`apps/api` + `packages/api-core`). Next.js route handlers are thin proxies only.

### Fastify Route Pattern (Primary)

**File location**: `apps/api/src/routes/v1/[resource]/index.ts`

**Complete route example**:
```typescript
// apps/api/src/routes/v1/leads/index.ts

import { FastifyPluginAsync } from 'fastify'
import { Type, Static } from '@sinclair/typebox'
import { prisma } from '@/lib/prisma'

// TypeBox schemas for validation
const QuerySchema = Type.Object({
  status: Type.Optional(Type.Union([
    Type.Literal('DISCOVERED'),
    Type.Literal('ENGAGED'),
    Type.Literal('QUALIFIED'),
  ])),
  page: Type.Optional(Type.Number({ minimum: 1, default: 1 })),
  limit: Type.Optional(Type.Number({ minimum: 1, maximum: 100, default: 20 })),
})

const LeadSchema = Type.Object({
  id: Type.String(),
  name: Type.String(),
  status: Type.String(),
  createdAt: Type.String(),
})

const LeadsResponseSchema = Type.Object({
  data: Type.Array(LeadSchema),
  pagination: Type.Object({
    page: Type.Number(),
    limit: Type.Number(),
    total: Type.Number(),
  }),
})

type QueryType = Static<typeof QuerySchema>

const leadsRoutes: FastifyPluginAsync = async (fastify) => {
  // GET /api/v1/leads
  fastify.get<{ Querystring: QueryType }>(
    '/',
    {
      schema: {
        querystring: QuerySchema,
        response: {
          200: LeadsResponseSchema,
        },
      },
      preHandler: [fastify.authenticate], // Auth hook
    },
    async (request, reply) => {
      const { status, page = 1, limit = 20 } = request.query

      const where = status ? { status } : {}

      const [leads, total] = await Promise.all([
        prisma.lead.findMany({
          where,
          skip: (page - 1) * limit,
          take: limit,
          orderBy: { createdAt: 'desc' },
        }),
        prisma.lead.count({ where }),
      ])

      return {
        data: leads,
        pagination: { page, limit, total },
      }
    }
  )

  // POST /api/v1/leads
  fastify.post<{ Body: { name: string; status: string } }>(
    '/',
    {
      schema: {
        body: Type.Object({
          name: Type.String({ minLength: 1, maxLength: 255 }),
          status: Type.Union([
            Type.Literal('DISCOVERED'),
            Type.Literal('ENGAGED'),
            Type.Literal('QUALIFIED'),
          ]),
        }),
        response: {
          201: Type.Object({ data: LeadSchema }),
        },
      },
      preHandler: [fastify.authenticate, fastify.requireRole('admin', 'manager')],
    },
    async (request, reply) => {
      const lead = await prisma.lead.create({
        data: request.body,
      })

      reply.status(201)
      return { data: lead }
    }
  )
}

export default leadsRoutes
```

### Fastify Plugin Patterns

**Authentication plugin**:
```typescript
// apps/api/src/plugins/auth.ts
import fp from 'fastify-plugin'
import { FastifyPluginAsync } from 'fastify'

declare module 'fastify' {
  interface FastifyInstance {
    authenticate: (request: FastifyRequest, reply: FastifyReply) => Promise<void>
    requireRole: (...roles: string[]) => (request: FastifyRequest, reply: FastifyReply) => Promise<void>
  }
  interface FastifyRequest {
    user: { id: string; email: string; role: string }
  }
}

const authPlugin: FastifyPluginAsync = async (fastify) => {
  fastify.decorate('authenticate', async (request, reply) => {
    const token = request.headers.authorization?.replace('Bearer ', '')
    if (!token) {
      reply.status(401).send({ error: 'Unauthorized' })
      return
    }

    try {
      const user = await verifyToken(token)
      request.user = user
    } catch {
      reply.status(401).send({ error: 'Invalid token' })
    }
  })

  fastify.decorate('requireRole', (...roles: string[]) => {
    return async (request, reply) => {
      if (!roles.includes(request.user.role)) {
        reply.status(403).send({ error: 'Forbidden' })
      }
    }
  })
}

export default fp(authPlugin, { name: 'auth' })
```

### Fastify Schema Validation

**Using TypeBox (recommended)**:
```typescript
import { Type, Static } from '@sinclair/typebox'

// Define schema
const CreateLeadSchema = Type.Object({
  name: Type.String({ minLength: 1, maxLength: 255 }),
  email: Type.String({ format: 'email' }),
  status: Type.Union([
    Type.Literal('DISCOVERED'),
    Type.Literal('ENGAGED'),
  ]),
})

// Extract TypeScript type
type CreateLeadInput = Static<typeof CreateLeadSchema>

// Use in route
fastify.post<{ Body: CreateLeadInput }>('/', {
  schema: { body: CreateLeadSchema },
  handler: async (request) => {
    // request.body is fully typed
    const lead = await createLead(request.body)
    return { data: lead }
  },
})
```

### Error Handling in Fastify

```typescript
// apps/api/src/plugins/error-handler.ts
import fp from 'fastify-plugin'
import { FastifyPluginAsync } from 'fastify'

const errorHandler: FastifyPluginAsync = async (fastify) => {
  fastify.setErrorHandler((error, request, reply) => {
    // Validation errors from schema
    if (error.validation) {
      return reply.status(400).send({
        error: 'Validation failed',
        details: error.validation,
      })
    }

    // Known application errors
    if (error.statusCode && error.statusCode < 500) {
      return reply.status(error.statusCode).send({
        error: error.message,
      })
    }

    // Log unexpected errors
    fastify.log.error(error)

    // Return generic error (don't expose internals)
    return reply.status(500).send({
      error: 'Internal server error',
    })
  })
}

export default fp(errorHandler, { name: 'error-handler' })
```

### Key Patterns

- Export routes as `FastifyPluginAsync` for proper typing
- Use `preHandler` hooks for authentication/authorization
- Define schemas with TypeBox for runtime validation + TypeScript types
- Use `fastify.log` for structured logging
- Register plugins with `fastify-plugin` (fp) for encapsulation control
- Keep business logic in service layer (`packages/api-core`), routes are thin
