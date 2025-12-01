### Fastify route pattern (primary)

**File location**: `apps/dashboard/src/app/api/v1/dashboard/[resource]/route.ts`

**Example**:
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

// ✅ CORRECT - Next.js 16 route handler
export async function GET(request: NextRequest) {
  try {
    // 1. Authentication (Better-Auth)
    const user = await requireAuth(request)

    // 2. Validate query parameters
    const { searchParams } = new URL(request.url)
    const query = QuerySchema.parse({
      status: searchParams.get('status'),
      page: searchParams.get('page'),
      limit: searchParams.get('limit'),
    })

    // 3. Database query (Prisma)
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

// POST handler
export async function POST(request: NextRequest) {
  const user = await requireAuth(request)
  const body = await request.json()

  // Validate request body
  const BodySchema = z.object({
    name: z.string().min(1).max(255),
    status: z.enum(['DISCOVERED', 'ENGAGED', 'QUALIFIED']),
  })

  const validated = BodySchema.parse(body)

  const lead = await prisma.lead.create({
    data: validated,
  })

  return NextResponse.json({ data: lead }, { status: 201 })
}
```

### Next.js proxy handler (thin) – example
```typescript
// apps/dashboard/src/app/api/v1/leads/route.ts
import { NextRequest, NextResponse } from 'next/server'

export async function GET(req: NextRequest) {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL!
  const upstream = new URL(req.url)
  const r = await fetch(`${apiBase}${upstream.pathname}?${upstream.searchParams}`, {
    headers: { Authorization: req.headers.get('authorization') || '' },
  })
  return NextResponse.json(await r.json(), { status: r.status })
}
```

**Key patterns**:
- ✅ Export named functions: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- ✅ Accept `NextRequest` parameter
- ✅ Return `NextResponse` objects
- ✅ Use `requireAuth()` for authentication
- ✅ Use Zod for validation
- ✅ Use Prisma for database queries
