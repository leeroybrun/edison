## TypeScript Validation Context (Claude)

### Type Safety
- Enforce `strict` mode for all TS projects.
- Avoid `any` unless justified with comments and tests.
- Prefer explicit return types on exported functions.
- For public APIs, use interfaces/types with clear generics.

### Linting & Type‑Checking
- `npm run typecheck` must pass with zero errors.
- No `@ts-ignore` or `@ts-expect-error` without issue link and scope.

