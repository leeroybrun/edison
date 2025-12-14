# Type Safety Patterns

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Prefer discriminated unions over optional fields.
- Use `satisfies` for config objects (prevents excess properties without widening).
- Constrain generics.

```ts
type Result =
  | { ok: true; value: string }
  | { ok: false; error: string }

const cfg = {
  mode: 'prod',
} satisfies { mode: 'prod' | 'dev' }
```
<!-- /section: patterns -->
