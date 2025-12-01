# global overlay for Vitest pack

<!-- EXTEND: TechStack -->
## Vitest Validation Context

### Guidelines
{{include:.edison/_generated/guidelines/vitest/tdd-workflow.md}}
{{include:.edison/_generated/guidelines/vitest/test-quality.md}}
{{include:.edison/_generated/guidelines/vitest/api-testing.md}}
{{include:.edison/_generated/guidelines/vitest/component-testing.md}}

### Concrete Checks
- Follow RED→GREEN→REFACTOR; tests precede implementation.
- Avoid `.skip()`/`.only()` in committed code.
- Prefer realistic tests with minimal mocking; isolate side effects.
- Keep tests fast and deterministic with clear naming.
<!-- /EXTEND -->
