# React Hooks (React 19)

## Core Rules

- Only call hooks at the top level of components or custom hooks.
- Derive state; avoid redundant `useState` when values can be computed.
- Memoize expensive calculations with `useMemo`; keep dependencies minimal and explicit.
- Use `useCallback` to stabilize function props when needed.

## React 19 Features

### use() Hook - Promise Unwrapping

The `use()` hook is a React 19 feature that allows you to unwrap promises in components.

```typescript
// ✅ CORRECT - use() for promise unwrapping
import { use } from 'react'

export function DataComponent({ dataPromise }) {
  const data = use(dataPromise)  // Unwraps promise
  return <div>{data.name}</div>
}
```

**When to use use()**:
- Unwrap promises passed from server components
- Handle async data in client components
- Works with error boundaries for error handling
- Reduces need for useEffect data fetching

### useFormStatus (React 19 Hook)

The `useFormStatus` hook provides information about the pending state of a form submission.

```typescript
'use client'

import { useFormStatus } from 'react-dom'

export function SubmitButton() {
  const { pending } = useFormStatus()
  
  return (
    <button disabled={pending} type="submit">
      {pending ? 'Submitting...' : 'Submit'}
    </button>
  )
}
```

**Features**:
- `pending`: boolean indicating if form submission is in progress
- Only works with `<form>` elements
- Automatically connected to nearest parent form

### useOptimistic (React 19 Hook)

The `useOptimistic` hook updates the UI optimistically while a server action is in progress.

```typescript
'use client'

import { useOptimistic } from 'react'

export function LikeButton({ postId, initialLikes }) {
  const [likes, optimisticLikes] = useOptimistic(
    initialLikes,
    (currentLikes, newLikes) => newLikes
  )
  
  async function handleLike() {
    // Optimistically update UI
    optimisticLikes(likes + 1)
    // Server action updates database
    await likePost(postId)
  }
  
  return (
    <button onClick={handleLike}>
      Like ({optimisticLikes})
    </button>
  )
}
```

**Benefits**:
- Responsive UI with server actions
- Automatic rollback if action fails
- Better UX for forms and mutations

## Standard Hooks

### useState

```typescript
const [state, setState] = useState<T>(initialValue)

// Lazy initialization for expensive calculations
const [data, setData] = useState<T>(() => expensiveInit())
```

### useEffect

```typescript
useEffect(() => {
  // Side effect
  return () => {
    // Cleanup
  }
}, [dependencies])
```

### useContext

```typescript
const value = useContext(MyContext)
```

### useReducer

```typescript
const [state, dispatch] = useReducer(reducer, initialState)
```

### useRef

```typescript
const ref = useRef<HTMLDivElement>(null)
```

### useMemo

```typescript
const value = useMemo(() => expensiveCalc(), [deps])
```

### useCallback

```typescript
const callback = useCallback(() => doSomething(), [deps])
```

