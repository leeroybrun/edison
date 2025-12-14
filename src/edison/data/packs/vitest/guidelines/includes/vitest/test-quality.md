# Test Quality

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
### Test quality (Vitest)

- Use descriptive `describe`/`it` names that state **behavior**.
- Prefer outcome assertions over internal call assertions.
- Prefer user-facing assertions for UI; avoid brittle snapshots unless they add real value.
- Ensure proper setup/teardown; avoid shared mutable state.

#### GOOD: behavior-focused, outcome assertions

```typescript
import { describe, it, expect } from 'vitest'

describe('createItem', () => {
  it('rejects empty name with a typed error', () => {
    expect(() => createItem({ name: '' })).toThrow(/name/i)
  })
})
```

#### BAD: implementation-detail assertions as “proof”

```typescript
import { it, expect } from 'vitest'

it('creates item', async () => {
  await createItem({ name: 'x' })

  // ❌ proves only that an internal method was called, not that behavior is correct
  expect(internalDbClient.insert).toHaveBeenCalled()
})
```
<!-- /section: patterns -->

