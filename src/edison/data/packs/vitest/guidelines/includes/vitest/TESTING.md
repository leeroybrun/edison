# Vitest Testing (Pack Guide)

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

See also:
- `packs/vitest/guidelines/includes/vitest/tdd-workflow.md`
- `packs/vitest/guidelines/includes/vitest/test-quality.md`
- `packs/vitest/guidelines/includes/vitest/api-testing.md`
- `packs/vitest/guidelines/includes/vitest/component-testing.md`

<!-- section: patterns -->
### Vitest fundamentals

- **Structure**: Keep tests small and explicit (arrange → act → assert).
- **Determinism**: Control time and randomness; avoid sleeps.
- **Isolation**: No shared mutable globals; reset state between tests.
- **Signals**: Assert outcomes (return values, state changes, emitted events), not internal call graphs.
- **Boundary doubles only**: If stubbing is unavoidable, do it only at external boundaries you do not control.
- **Guardrails**: Never commit `.only` / `.skip`.

### Deterministic time (GOOD vs BAD)

```typescript
import { describe, it, expect, vi } from 'vitest'

describe('time-dependent logic', () => {
  it('expires after ttl', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2025-01-01T00:00:00Z'))

    const ttlMs = 60_000
    const result = doSomethingTimeDependent({ ttlMs })

    vi.advanceTimersByTime(ttlMs)
    expect(result.isExpired()).toBe(true)

    vi.useRealTimers()
  })
})
```

```typescript
import { it } from 'vitest'

it('expires after ttl', async () => {
  await new Promise((r) => setTimeout(r, 60_000)) // ❌ flaky + slow
})
```

### Stubbing boundaries (only external services)

```typescript
import { vi, it, expect } from 'vitest'

it('handles external service error', async () => {
  // ✅ acceptable: stub ONLY the external boundary (e.g. fetch to third-party)
  vi.stubGlobal('fetch', async () => {
    return new Response(JSON.stringify({ error: 'rate limited' }), { status: 429 })
  })

  const result = await callExternalService()
  expect(result.ok).toBe(false)
})
```

```typescript
import { vi } from 'vitest'

// ❌ forbidden: mocking internal modules/services as “proof”
vi.mock('../services/items', () => ({ listItems: () => [] }))
```
<!-- /section: patterns -->
