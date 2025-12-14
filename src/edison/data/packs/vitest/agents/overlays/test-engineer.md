# test-engineer overlay for Vitest pack

<!-- extend: tools -->
- Vitest for unit/integration tests; config in `vitest.config.*`.
- Use your project's configured test commands (avoid hardcoding workspace filters/paths).
- Coverage: use the repo's configured coverage command/flags (avoid hardcoded thresholds in prompts).
<!-- /extend -->

<!-- extend: guidelines -->
- Apply Vitest-specific patterns for determinism, isolation, and boundary testing.
{{include-section:packs/vitest/guidelines/includes/vitest/TESTING.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/tdd-workflow.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/test-quality.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/api-testing.md#patterns}}
{{include-section:packs/vitest/guidelines/includes/vitest/component-testing.md#patterns}}
<!-- /extend -->





