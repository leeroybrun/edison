# Advanced Types

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Prefer `as const` for literal inference; avoid overusing `as` assertions.
- Use template literal types for expressive keys.

```ts
type EventName = `user.${'created' | 'deleted'}`

const status = {
  active: 'active',
  archived: 'archived',
} as const

type Status = (typeof status)[keyof typeof status]
```
<!-- /section: patterns -->
