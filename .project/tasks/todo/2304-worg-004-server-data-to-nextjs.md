<!-- TaskID: 2304-worg-004-server-data-to-nextjs -->
<!-- Priority: 2304 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: refactor -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave4 -->
<!-- EstimatedHours: 4 -->
<!-- DependsOn: Wave 3 -->

# WORG-004: Move Server-Driven Data Patterns to Next.js Pack

## Summary
Move server-driven data fetching patterns from Wilson overlays to the Edison nextjs pack.

## Problem Statement
Wilson overlays contain Next.js patterns that are NOT Wilson-specific:
- Server Component data fetching
- Server Actions patterns
- Streaming/Suspense patterns
- Cache configuration
- Revalidation strategies

These should be in the nextjs pack for all projects.

## Objectives
- [x] Identify server data patterns in Wilson overlays
- [x] Move to Edison nextjs pack
- [x] Keep Wilson API routes in overlays

## Source Files

### Wilson Overlays
```
/Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/
```

### Next.js Pack
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/nextjs/guidelines/
```

## Precise Instructions

### Step 1: Audit Wilson Overlays
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays
grep -rn "Server Component\|Server Action\|revalidate\|cache.*force\|Suspense\|streaming" . --include="*.md"
```

### Step 2: Content to Move

**Move to Next.js Pack:**
- Server Component data fetching
- Server Actions form handling
- Streaming with Suspense
- Cache and revalidate config
- ISR/SSG/SSR patterns
- Route segment config exports

**Keep in Wilson Overlays:**
- Wilson API route structure
- Wilson-specific server actions
- Wilson page organization

### Step 3: Update Next.js Pack

**Add/update `server-actions.md`:**
```markdown
# Server Actions

## Form Handling
```typescript
// app/actions.ts
'use server'

export async function createItem(formData: FormData) {
  const name = formData.get('name');

  // Validate
  if (!name) throw new Error('Name required');

  // Create
  const item = await db.item.create({ data: { name } });

  // Revalidate
  revalidatePath('/items');

  return item;
}
```

## Usage in Components
```tsx
import { createItem } from './actions';

export function Form() {
  return (
    <form action={createItem}>
      <input name="name" />
      <button type="submit">Create</button>
    </form>
  );
}
```

## Error Handling
```typescript
'use server'

export async function action() {
  try {
    // ...
  } catch (error) {
    // Return error for client handling
    return { error: 'Failed to create' };
  }
}
```
```

**Add/update `caching.md`:**
```markdown
# Data Caching

## Fetch Options
```typescript
// Cache forever (default)
fetch(url, { cache: 'force-cache' });

// No cache
fetch(url, { cache: 'no-store' });

// Revalidate every 60 seconds
fetch(url, { next: { revalidate: 60 } });
```

## Route Segment Config
```typescript
// Opt out of caching
export const dynamic = 'force-dynamic';

// Revalidate every hour
export const revalidate = 3600;
```

## On-Demand Revalidation
```typescript
import { revalidatePath, revalidateTag } from 'next/cache';

// Revalidate path
revalidatePath('/items');

// Revalidate tag
revalidateTag('items');
```
```

**Add/update `streaming.md`:**
```markdown
# Streaming and Suspense

## Streaming with Suspense
```tsx
import { Suspense } from 'react';

export default function Page() {
  return (
    <div>
      <h1>Dashboard</h1>
      <Suspense fallback={<Loading />}>
        <SlowComponent />
      </Suspense>
    </div>
  );
}
```

## loading.tsx
Automatic loading UI:
```
app/
  dashboard/
    loading.tsx   <- Shows while page loads
    page.tsx
```

## Parallel Data Fetching
```tsx
async function Page() {
  // Start both fetches immediately
  const userPromise = getUser();
  const postsPromise = getPosts();

  // Wait for both
  const [user, posts] = await Promise.all([
    userPromise,
    postsPromise
  ]);
}
```
```

### Step 4: Update Wilson Overlays

Keep only:
```markdown
# Wilson Next.js Overlay

## App Structure
- apps/dashboard/app - Main app
- apps/dashboard/components - Shared components

## API Routes
- /api/v1/dashboard/* - All dashboard APIs

## Server Actions
- See apps/dashboard/app/actions/
```

## Verification Checklist
- [ ] Server Actions in nextjs pack
- [ ] Caching/revalidation in pack
- [ ] Streaming patterns in pack
- [ ] Wilson overlays only have structure specifics

## Success Criteria
Any project using nextjs pack gets server data patterns.

## Related Issues
- Content Placement Audit: Wilson overlays 60% misplaced
