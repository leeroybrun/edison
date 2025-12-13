# global overlay for Vitest pack

<!-- extend: tech-stack -->
## Vitest Validation Context

### Guidelines
{{include:packs/vitest/guidelines/vitest/tdd-workflow.md}}
{{include:packs/vitest/guidelines/vitest/test-quality.md}}
{{include:packs/vitest/guidelines/vitest/api-testing.md}}
{{include:packs/vitest/guidelines/vitest/component-testing.md}}

### Concrete Checks
- Follow RED→GREEN→REFACTOR; tests precede implementation.
- Avoid `.skip()`/`.only()` in committed code.
- Prefer realistic tests with minimal mocking; isolate side effects.
- Keep tests fast and deterministic with clear naming.
<!-- /extend -->
