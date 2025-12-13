# component-builder overlay for Next.js pack

<!-- extend: tools -->
- Next.js 16 App Router components in `app/**` (or your project's equivalent root).
- React Server/Client Components with strict TypeScript.
- Run your project's lint/test commands for Next.js code (avoid hardcoded workspace filters).
<!-- /extend -->

<!-- extend: guidelines -->
- Default to Server Components; mark `"use client"` only when needed (state, effects, event handlers).
- Keep data fetching in Server Components; pass serialized props to clients.
- Use Next.js conventions: file-based routing, `route.ts` API proxies, metadata exports, and `next/image` for assets.
- Co-locate loading/error states with routes; avoid client-only data fetching unless required.
- Align with design system classes; prefer shared utilities from your project's shared library modules.
<!-- /extend -->

<!-- section: NextJSComponentPatterns -->
## Server Components (Default)

Server Components are the default in Next.js App Router. Use them for:
- Database queries
- API calls
- Heavy computations
- Sensitive data access

```tsx
// app/items/page.tsx - Server Component (default, no directive needed)

import { listItems } from '<data-access-module>'
import { ItemList } from '<component-module>'

// Server Component - can query database directly
export default async function ItemsPage() {
  // Direct data access - no client API hop needed
  const items = await listItems()

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold font-sans mb-6">Items</h1>
      <ItemList items={items} />
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

## Client Components (When Needed)

Client Components are required for interactivity (state, effects, event handlers, browser APIs).

```tsx
// app/items/ItemFilters.tsx
'use client'

import { useState } from 'react'

export function ItemFilters() {
  const [status, setStatus] = useState('all')
  return (
    <select value={status} onChange={(e) => setStatus(e.target.value)}>
      <option value="all">All</option>
      <option value="active">Active</option>
    </select>
  )
}
```

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
  const [items, metrics, activity] = await Promise.all([
    getItems(),
    getMetrics(),
    getActivity()
  ])

  return (
    <>
      <ItemsSummary items={items} />
      <MetricsDisplay data={metrics} />
      <ActivityFeed items={activity} />
    </>
  )
}
```

## Loading and Error States

```tsx
// app/items/loading.tsx
export default function Loading() {
  return <ItemsSkeleton />
}

// app/items/error.tsx
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
<!-- /section: NextJSComponentPatterns -->





