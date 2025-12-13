# testing overlay for Vitest pack

<!-- extend: checks -->
## Vitest Testing Context

### Guidelines
{{include:packs/vitest/guidelines/vitest/tdd-workflow.md}}
{{include:packs/vitest/guidelines/vitest/test-quality.md}}
{{include:packs/vitest/guidelines/vitest/api-testing.md}}
{{include:packs/vitest/guidelines/vitest/component-testing.md}}

### Vitest-Specific Checks
- Enforce RED→GREEN→REFACTOR with Vitest; block `.only` / `.skip` and reset mocks between tests.
- Prefer realistic integration-style tests using `vi.spyOn`/`vi.fn` minimally; avoid over-mocking prisma/auth helpers.
- Use Testing Library with Vitest for React components; assert real DOM output and user interactions.
- Run suites with coverage (`vitest --coverage`) and keep suites deterministic (no shared state, use fake timers when needed).
<!-- /extend -->
