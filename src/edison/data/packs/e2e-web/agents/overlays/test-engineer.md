---
name: test-engineer
pack: e2e-web
overlay_type: extend
---

<!-- extend: tools -->
### Web E2E (Playwright)

```bash
# Run E2E suite
npx playwright test

# Debug a failing test interactively
npx playwright test --ui
npx playwright test --headed
```
<!-- /extend -->

<!-- extend: guidelines -->
### Web E2E Patterns (Playwright)

{{include-section:packs/e2e-web/guidelines/includes/e2e-web/PLAYWRIGHT.md#agent-patterns}}
<!-- /extend -->

