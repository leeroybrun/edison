# global overlay for TypeScript pack

<!-- extend: tech-stack -->
## TypeScript Validation Context

### Guidelines
{{include-section:packs/typescript/guidelines/includes/typescript/strict-mode.md#patterns}}
{{include-section:packs/typescript/guidelines/includes/typescript/type-safety.md#patterns}}
{{include-section:packs/typescript/guidelines/includes/typescript/advanced-types.md#patterns}}

### Type Safety
- Enforce `strict` mode for all TS projects.
- Avoid `any` unless justified with comments and tests.
- Prefer explicit return types on exported functions.
- For public APIs, use interfaces/types with clear generics.

### Linting & Type-Checking
- `{{fn:ci_command("type-check")}}` must pass with zero errors.
- No `@ts-ignore` or `@ts-expect-error` without issue link and scope.
<!-- /extend -->
