# component-builder overlay for Next.js pack

<!-- EXTEND: Tools -->
- Next.js 16 App Router components in `apps/dashboard/src/app/**`.
- React Server/Client Components with strict TypeScript.
- `pnpm lint --filter dashboard` and `pnpm test --filter dashboard`.
<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->
- Default to Server Components; mark `"use client"` only when needed (state, effects, event handlers).
- Keep data fetching in Server Components; pass serialized props to clients.
- Use Next.js conventions: file-based routing, `route.ts` API proxies, metadata exports, and `next/image` for assets.
- Co-locate loading/error states with routes; avoid client-only data fetching unless required.
- Align with design system classes; prefer shared utilities from `@/lib/*`.
<!-- /EXTEND -->

<!-- SECTION: NextJSComponentPatterns -->
## Server Components (Default)

Server Components are the default in Next.js App Router. Use them for:
- Database queries
- API calls
- Heavy computations
- Sensitive data access

```tsx
// app/leads/page.tsx - Server Component (default, no directive needed)

import { prisma } from '@/lib/prisma'
import { LeadList } from '@/components/leads/LeadList'

// Server Component - can query database directly
export default async function LeadsPage() {
  // Direct database query - no API needed
  const leads = await prisma.lead.findMany()

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold font-sans mb-6">Leads</h1>
      <LeadList leads={leads} />
    </div>
  )
}
```

**Server Component features**:
- Can query database directly
- Can use async/await in component body
- No client-side JavaScript sent to browser
- Better performance (code stays on server)
- Can access server-only resources (env vars, file system)

## Server vs Client Decision Tree

| Need | Use |
|------|-----|
| Database query | Server Component |
| API call with secrets | Server Component |
| Static content | Server Component |
| useState/useEffect | Client Component |
| onClick/onChange | Client Component |
| Browser APIs (localStorage) | Client Component |
| Animations | Client Component |
| Third-party hooks | Client Component |

## Data Fetching Patterns

### Server-Side Fetch

```tsx
// app/dashboard/page.tsx
async function getMetrics() {
  const res = await fetch('https://api.example.com/metrics', {
    next: { revalidate: 60 }  // Cache for 60 seconds
  })
  return res.json()
}

export default async function DashboardPage() {
  const metrics = await getMetrics()
  return <MetricsDisplay data={metrics} />
}
```

### Parallel Data Fetching

```tsx
// Fetch multiple data sources in parallel
export default async function DashboardPage() {
  const [leads, metrics, activity] = await Promise.all([
    getLeads(),
    getMetrics(),
    getActivity()
  ])

  return (
    <>
      <LeadsSummary leads={leads} />
      <MetricsDisplay data={metrics} />
      <ActivityFeed items={activity} />
    </>
  )
}
```

## Loading and Error States

```tsx
// app/leads/loading.tsx
export default function Loading() {
  return <LeadsSkeleton />
}

// app/leads/error.tsx
'use client'

export default function Error({
  error,
  reset
}: {
  error: Error
  reset: () => void
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={reset}>Try again</button>
    </div>
  )
}
```
<!-- /SECTION: NextJSComponentPatterns -->





