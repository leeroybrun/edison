# global overlay for Vitest pack

<!-- EXTEND: TechStack -->
## Vitest Validation Context

### Guidelines
{{include:.edison/packs/vitest/guidelines/tdd-workflow.md}}
{{include:.edison/packs/vitest/guidelines/test-quality.md}}
{{include:.edison/packs/vitest/guidelines/api-testing.md}}
{{include:.edison/packs/vitest/guidelines/component-testing.md}}

### Concrete Checks
- Follow RED→GREEN→REFACTOR; tests precede implementation.
- Avoid `.skip()`/`.only()` in committed code.
- Prefer realistic tests with minimal mocking; isolate side effects.
- Keep tests fast and deterministic with clear naming.
<!-- /EXTEND -->
