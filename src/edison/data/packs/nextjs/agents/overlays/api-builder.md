# api-builder overlay for Next.js pack

<!-- EXTEND: Tools -->
- Next.js App Router route handlers in `apps/dashboard/src/app/api/**/route.ts`.
- `requireAuth` helper from `@/lib/auth/api-helpers` (authentication).
- Prisma client `@/lib/prisma` and Zod for validation.
- `pnpm lint --filter dashboard` and `pnpm test --filter dashboard` for API routes.
<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->
### Key Patterns
- Export named functions: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- Accept `NextRequest` parameter
- Return `NextResponse` objects
- Use `requireAuth()` for authentication
- Use Zod for validation
- Use Prisma for database queries (when not proxying)
<!-- /EXTEND -->

<!-- NEW_SECTION: NextJSRoutePatterns -->
### Next.js Route Handler Pattern (Full Implementation)

**File location**: `apps/dashboard/src/app/api/v1/[resource]/route.ts`

**Complete example**:
```typescript
// apps/dashboard/src/app/api/v1/dashboard/leads/route.ts

import { NextRequest, NextResponse } from 'next/server'
import { requireAuth } from '@/lib/auth/api-helpers'
import { prisma } from '@/lib/prisma'
import { z } from 'zod'

// Zod schema for validation
const QuerySchema = z.object({
  status: z.enum(['DISCOVERED', 'ENGAGED', 'QUALIFIED']).optional(),
  page: z.coerce.number().min(1).default(1),
  limit: z.coerce.number().min(1).max(100).default(20),
})

// GET /api/v1/dashboard/leads
export async function GET(request: NextRequest) {
  try {
    // 1. Authentication
    const user = await requireAuth(request)

    // 2. Validate query parameters
    const { searchParams } = new URL(request.url)
    const query = QuerySchema.parse({
      status: searchParams.get('status'),
      page: searchParams.get('page'),
      limit: searchParams.get('limit'),
    })

    // 3. Database query
    const leads = await prisma.lead.findMany({
      where: query.status ? { status: query.status } : {},
      skip: (query.page - 1) * query.limit,
      take: query.limit,
      orderBy: { createdAt: 'desc' },
    })

    // 4. Return NextResponse
    return NextResponse.json({ data: leads }, { status: 200 })
  } catch (error) {
    // 5. Error handling
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid query parameters', details: error.flatten() },
        { status: 400 }
      )
    }

    if (error.message === 'Unauthorized') {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    console.error('API error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

### Next.js Proxy Handler Pattern (Thin)

When a Fastify upstream exists, use thin proxy handlers:

```typescript
// apps/dashboard/src/app/api/v1/leads/route.ts
import { NextRequest, NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL!

export async function GET(req: NextRequest) {
  const upstream = new URL(req.url)
  const response = await fetch(
    `${API_BASE}${upstream.pathname}?${upstream.searchParams}`,
    {
      headers: {
        Authorization: req.headers.get('authorization') || '',
        'Content-Type': 'application/json',
      },
    }
  )

  return NextResponse.json(await response.json(), { status: response.status })
}
```

### Error Handling Pattern (Next.js)

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { Prisma } from '@prisma/client'

export async function handler(request: NextRequest) {
  try {
    const result = await someOperation()
    return NextResponse.json({ data: result })
  } catch (error) {
    // Zod validation errors
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Validation failed', details: error.flatten() },
        { status: 400 }
      )
    }

    // Prisma unique constraint violation
    if (error instanceof Prisma.PrismaClientKnownRequestError) {
      if (error.code === 'P2002') {
        return NextResponse.json(
          { error: 'Resource already exists' },
          { status: 409 }
        )
      }
    }

    console.error('API error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

### Dynamic Route Segments

```typescript
// apps/dashboard/src/app/api/v1/leads/[id]/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { requireAuth } from '@/lib/auth/api-helpers'
import { prisma } from '@/lib/prisma'

interface RouteParams {
  params: Promise<{ id: string }>
}

export async function GET(
  request: NextRequest,
  { params }: RouteParams
) {
  const user = await requireAuth(request)
  const { id } = await params

  const lead = await prisma.lead.findUnique({
    where: { id },
  })

  if (!lead) {
    return NextResponse.json(
      { error: 'Lead not found' },
      { status: 404 }
    )
  }

  return NextResponse.json({ data: lead })
}
```

### Summary

- Keep handlers thin: authenticate with `requireAuth`, validate input with Zod, and return `NextResponse` objects with structured error envelopes.
- Use pagination bounds (`page`, `limit`), typed enums for statuses, and consistent ordering; avoid unbounded queries.
- When a Fastify upstream exists, treat the handler as a proxy: forward auth headers, propagate status codes, and do not reimplement business logic.
<!-- /NEW_SECTION -->





