### Server Components (Default)

```tsx
// app/leads/page.tsx - Server Component (default)

import { prisma } from '@/lib/prisma'
import { LeadList } from '@/components/leads/LeadList'

// ✅ Server Component - can query database directly
export default async function LeadsPage() {
  // Direct database query
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
- ✅ Can query database directly
- ✅ Can use async/await in component
- ✅ No client-side JavaScript sent
- ✅ Better performance

### Client Components (When Needed)

```tsx
// components/leads/LeadList.tsx - Client Component

'use client'  // ✅ Explicit directive

import { useState } from 'react'
import { motion } from 'motion/react'

export function LeadList({ leads }) {
  const [filter, setFilter] = useState('')

  return (
    <div>
      <input
        type="text"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="w-full px-4 py-2 bg-[#1a1a1a] border border-[#222222] rounded-md font-sans"
        placeholder="Filter leads..."
      />

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mt-4 space-y-2"
      >
        {leads
          .filter((lead) => lead.name.includes(filter))
          .map((lead) => (
            <LeadCard key={lead.id} lead={lead} />
          ))}
      </motion.div>
    </div>
  )
}
```

**Client Component requirements**:
- ✅ Use `'use client'` directive
- ✅ Required for: hooks, browser APIs, interactions, animations
- ✅ Can import Server Components as children
