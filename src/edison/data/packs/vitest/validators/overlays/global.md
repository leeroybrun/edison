# global overlay for Vitest pack

<!-- extend: tech-stack -->
## Vitest Validation Context

### Guidelines
{{include-section:packs/vitest/guidelines/includes/vitest/tdd-workflow.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/test-quality.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/api-testing.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/component-testing.md#patterns}}

### Concrete Checks
- Follow RED→GREEN→REFACTOR; tests precede implementation.
- Avoid `.skip()`/`.only()` in committed code.
- Prefer realistic tests with minimal mocking; isolate side effects.
- Keep tests fast and deterministic with clear naming.
<!-- /extend -->
