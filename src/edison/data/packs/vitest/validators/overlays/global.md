# global overlay for Vitest pack

<!-- extend: tech-stack -->
## Vitest Validation Context

### Guidelines
{{include-section:packs/vitest/guidelines/includes/vitest/tdd-workflow.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/test-quality.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/api-testing.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/component-testing.md#patterns}}

### Concrete Checks
- Avoid `.skip()`/`.only()` in committed code.
- Enforce the core NO MOCKS policy: mock only system boundaries (third-party APIs), never internal modules.
- Keep tests fast and deterministic with clear naming.
<!-- /extend -->
