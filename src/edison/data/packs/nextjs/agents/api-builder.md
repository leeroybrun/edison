# api-builder-nextjs (App Router)

## Tools
- Next.js 16 App Router route handlers in `apps/dashboard/src/app/api/**/route.ts`.
- `requireAuth` helper from `@/lib/auth/api-helpers` (Better-Auth).
- Prisma client `@/lib/prisma` and Zod 4 for validation.
- `pnpm lint --filter dashboard` and `pnpm test --filter dashboard` for API routes.

## Guidelines
- Keep handlers thin: authenticate with `requireAuth`, validate input with Zod, and return `NextResponse` objects with structured error envelopes.
- Use pagination bounds (`page`, `limit`), typed enums for statuses, and consistent ordering; avoid unbounded queries.
- When a Fastify upstream exists, treat the handler as a proxy—forward auth headers, propagate status codes, and do not reimplement business logic.
- Prefer shared helpers in `@/lib/*`; keep logging minimal and structured.
- Example pattern:
```typescript
export async function GET(request: NextRequest) {
  const user = await requireAuth(request)
  const { searchParams } = new URL(request.url)
  const query = QuerySchema.parse({
    status: searchParams.get('status'),
    page: z.coerce.number().min(1).default(1).parse(searchParams.get('page')),
    limit: z.coerce.number().min(1).max(100).default(20).parse(searchParams.get('limit')),
  })

  const data = await prisma.lead.findMany({
    where: query.status ? { status: query.status } : {},
    skip: (query.page - 1) * query.limit,
    take: query.limit,
    orderBy: { createdAt: 'desc' },
  })

  return NextResponse.json({ data })
}
```
