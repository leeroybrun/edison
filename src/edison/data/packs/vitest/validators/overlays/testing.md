# testing overlay for Vitest pack

<!-- extend: checks -->
## Vitest Testing Context

### Guidelines
{{include-section:packs/vitest/guidelines/includes/vitest/tdd-workflow.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/test-quality.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/api-testing.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/component-testing.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/TESTING.md#patterns}}

### Vitest-Specific Checks
- Block `.only` / `.skip` and ensure tests don't leak state between runs.
- Enforce the core NO MOCKS policy: use `vi.spyOn`/`vi.fn` only at system boundaries (third-party calls), never to “prove” internal behavior.
- Use Testing Library with Vitest for React components; assert real DOM output and user interactions.
- Run suites with coverage (`vitest --coverage`) and keep suites deterministic (no shared state, use fake timers when needed).
<!-- /extend -->
