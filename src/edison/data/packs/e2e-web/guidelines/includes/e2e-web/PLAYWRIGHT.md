# Playwright E2E (Web)

<!-- SECTION: agent-patterns -->
## Agent Patterns: Real, Unmocked E2E

### Test Like a User (Selectors)
- Prefer user-facing locators (`getByRole`, `getByLabel`, `getByText`) over CSS/XPath.
- Add stable identifiers only when necessary (`data-testid`) and keep them semantic.
- Avoid asserting on implementation details (DOM structure, CSS classes) unless that is the feature.

### Waiting & Determinism (No Flakes)
- Never use fixed sleeps/timeouts to “fix” timing.
- Rely on Playwright auto-waiting + web-first assertions (`expect(locator).toBeVisible()`).
- Assert *state changes* rather than intermediate transitions.
- Make every test independent:
  - isolate user/session per test
  - isolate created records (unique namespaces/IDs)
  - never depend on test order

### Real Setup (No Internal Mocks)
- Seed via real APIs or real DB utilities, not internal mocks.
- Prefer *arrange via the UI only when the UI is the feature*; otherwise arrange via stable APIs/fixtures and assert via UI.
- Avoid network interception (`route.fulfill`) for internal endpoints; only consider it for true third-party services you do not control.

### Coverage That Matters
For each user-visible change, ensure tests cover:
- Happy path
- Validation errors
- Permissions/auth edge cases
- Empty/loading/error states
- Keyboard-only path for critical interactions

### Debugging Toolkit
- Enable traces on failure in CI.
- Keep screenshots/videos on failure only; don’t generate noise for green runs.
- When debugging: run single worker, headed, with slowMo only temporarily.
<!-- /SECTION: agent-patterns -->

<!-- SECTION: test-architecture -->
## Suggested E2E Test Architecture

Recommended structure (adapt to project conventions):

```
e2e/
  specs/                  # user-facing flows
  fixtures/               # stable data builders (API-level)
  pages/                  # page objects only for complex UIs (optional)
  utils/                  # auth helpers, selectors, polling helpers
playwright.config.*       # baseURL, projects, retries, tracing
```

Rules:
- Keep helpers small and composable; avoid monolithic Page Objects.
- Centralize auth bootstrapping to keep tests fast (e.g., storageState), but do not bypass real auth in ways that invalidate behavior.
- Use config to control retries/timeouts/tracing; do not hardcode in tests.
<!-- /SECTION: test-architecture -->

<!-- SECTION: validator-protocol -->
## Validator Protocol: Browser Validation via Playwright MCP

When validating UI changes:
- Identify affected user journeys from the diff and acceptance criteria.
- Validate each journey in a real browser session with realistic input.
- Try to break flows: invalid inputs, rapid clicks, back/refresh, deep links, unauthenticated access.
- Confirm accessibility basics: keyboard navigation for primary flows, visible focus, correct roles/labels.

If Playwright MCP tools are unavailable:
- Fall back to running `playwright test` locally and reviewing traces/screenshots.
- Report the missing tooling as a blocking setup issue when UI changes require browser validation.
<!-- /SECTION: validator-protocol -->

