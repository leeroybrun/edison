# testing overlay for Vitest pack

<!-- EXTEND: Checks -->
## Vitest Testing Context

### Guidelines
{{include:.edison/packs/vitest/guidelines/tdd-workflow.md}}
{{include:.edison/packs/vitest/guidelines/test-quality.md}}
{{include:.edison/packs/vitest/guidelines/api-testing.md}}
{{include:.edison/packs/vitest/guidelines/component-testing.md}}

### Vitest-Specific Checks
- Enforce RED→GREEN→REFACTOR with Vitest; block `.only` / `.skip` and reset mocks between tests.
- Prefer realistic integration-style tests using `vi.spyOn`/`vi.fn` minimally; avoid over-mocking prisma/auth helpers.
- Use Testing Library with Vitest for React components; assert real DOM output and user interactions.
- Run suites with coverage (`vitest --coverage`) and keep suites deterministic (no shared state, use fake timers when needed).
<!-- /EXTEND -->
