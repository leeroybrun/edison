# component-builder-react (React 19)

## Tools
- React 19 with strict TypeScript; hooks/components in `apps/dashboard/src/**`.
- Testing with Vitest/RTL via `pnpm test --filter dashboard`.
- Motion 12.23+ for animations (formerly Framer Motion).
- Zod for form validation schemas.

## Guidelines
- Favor composition and pure components; avoid side effects in render paths.
- Use `use`/Server Components patterns when inside Next.js, otherwise standard client components with suspense-ready data flows.
- Keep props typed, stable, and documented; lift shared state; memoize where performance matters.
- Ensure accessibility (labels, focus, keyboard) and responsive layouts aligned to design system.

## Client Components Pattern

When you need interactivity, state, or browser APIs, use the `'use client'` directive:

```tsx
'use client'  // REQUIRED for hooks, events, browser APIs

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
        className="w-full px-4 py-2 rounded-md font-sans"
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
- Use `'use client'` directive at top of file
- Required for: hooks, browser APIs, interactions, animations
- Can import Server Components as children

## React Hooks Patterns

### useState with TypeScript

```tsx
const [items, setItems] = useState<Item[]>([])
const [selected, setSelected] = useState<string | null>(null)
```

### useEffect Cleanup

```tsx
useEffect(() => {
  const controller = new AbortController()

  fetchData({ signal: controller.signal })
    .then(setData)
    .catch(err => {
      if (err.name !== 'AbortError') throw err
    })

  return () => controller.abort()
}, [dependency])
```

## Forms with Validation

```tsx
'use client'

import { useState } from 'react'
import { z } from 'zod'

const leadSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email'),
})

export function LeadForm() {
  const [errors, setErrors] = useState<Record<string, string>>({})

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)

    const data = {
      name: formData.get('name') as string,
      email: formData.get('email') as string,
    }

    const result = leadSchema.safeParse(data)
    if (!result.success) {
      setErrors(result.error.flatten().fieldErrors)
      return
    }

    // Submit to API
    await fetch('/api/v1/leads', {
      method: 'POST',
      body: JSON.stringify(result.data),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium font-sans mb-1">
          Name
        </label>
        <input
          name="name"
          className="w-full px-4 py-2 border rounded-md font-sans"
        />
        {errors.name && (
          <p className="text-red-500 text-sm mt-1 font-sans">{errors.name}</p>
        )}
      </div>

      <button
        type="submit"
        className="px-4 py-2 rounded-md font-sans font-semibold transition-colors"
      >
        Submit
      </button>
    </form>
  )
}
```

## Animations with Motion 12

```tsx
import { motion } from 'motion/react'  // NOTE: 'motion/react' not 'framer-motion'

export function AnimatedCard({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="rounded-lg p-6"
    >
      {children}
    </motion.div>
  )
}

// List animations with stagger
export function AnimatedList({ items }) {
  return (
    <motion.ul
      initial="hidden"
      animate="visible"
      variants={{
        visible: {
          transition: {
            staggerChildren: 0.1
          }
        }
      }}
    >
      {items.map(item => (
        <motion.li
          key={item.id}
          variants={{
            hidden: { opacity: 0, x: -20 },
            visible: { opacity: 1, x: 0 }
          }}
        >
          {item.name}
        </motion.li>
      ))}
    </motion.ul>
  )
}
```

**Motion 12 Key Points**:
- Import from `motion/react` (not `framer-motion`)
- Use `AnimatePresence` for exit animations
- Prefer `variants` for coordinated animations
