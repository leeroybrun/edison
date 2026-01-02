# Playwright E2E (Web)

> Include-only guideline. Do not read directly; include specific parts via `include-section` (e.g. `{{include-section:packs/e2e-web/guidelines/includes/e2e-web/PLAYWRIGHT.md#agent-patterns}}`).

<!-- section: agent-patterns -->
## Agent Patterns: Real, Unmocked E2E

### Test Like a User (Selectors)
- Prefer user-facing locators (`getByRole`, `getByLabel`, `getByText`) over CSS/XPath.
- Use locator chaining/filtering to narrow scope instead of relying on brittle selectors.
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

### Authentication & Sessions (Speed + Isolation)
- Prefer **real auth** while keeping runs fast:
  - Authenticate once in a dedicated setup flow, save `storageState`, and reuse it to bootstrap tests already signed in.
  - If tests mutate server-side state (or run heavily in parallel), use **different accounts** or isolate state per test/role.
- If you use a setup project, be aware it can run even when a subset of tests doesn’t need auth; optimize only if it becomes a bottleneck (do not trade away correctness).

### Real Setup (No Internal Mocks)
- Seed via real APIs or real DB utilities, not internal mocks.
- Prefer *arrange via the UI only when the UI is the feature*; otherwise arrange via stable APIs/fixtures and assert via UI.
- Avoid network interception (`route.fulfill`) for internal endpoints; only consider it for true third-party services you do not control.

### Diagnostics & CI Evidence (Trace-Driven Debugging)
- Enable retries on CI (0 locally, >0 on CI) and collect evidence on failures:
  - `trace: 'on-first-retry'` for a good signal/cost tradeoff.
  - `video: 'on-first-retry'` and `screenshot: 'only-on-failure'` when flake triage needs more visibility.
- Prefer debugging from traces (timeline + snapshots) before changing waits/selectors.

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
<!-- /section: agent-patterns -->

<!-- section: test-architecture -->
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
- Centralize auth bootstrapping to keep tests fast (e.g., `storageState`), but do not bypass real auth in ways that invalidate behavior.
- Use config to control retries/timeouts/tracing; do not hardcode in tests.
- Prefer a sane default configuration profile:
  - `fullyParallel: true`
  - `forbidOnly: !!process.env.CI`
  - `retries: process.env.CI ? 2 : 0`
  - `workers: process.env.CI ? 1 : undefined`
  - `reporter: 'html'`
  - `use.trace: 'on-first-retry'`
<!-- /section: test-architecture -->

<!-- section: validator-protocol -->
## Validator Protocol: Browser Validation via Playwright MCP

When validating UI changes:
- Identify affected user journeys from the diff and acceptance criteria.
- Validate each journey in a real browser session with realistic input.
- Try to break flows: invalid inputs, rapid clicks, back/refresh, deep links, unauthenticated access.
- Confirm accessibility basics: keyboard navigation for primary flows, visible focus, correct roles/labels.

### Playwright MCP Notes (Deterministic, Accessibility-First)
- Prefer structured, deterministic snapshots (accessibility tree) over screenshot-based guessing.
- Use **isolated** browser sessions for validation by default (avoid accidental state leakage across runs).
- If you need a pre-authenticated state for validation, provide it via storage state (rather than manually “clicking login” every time).

If Playwright MCP tools are unavailable:
- Fall back to running `playwright test` locally and reviewing traces/screenshots.
- Report the missing tooling as a blocking setup issue when UI changes require browser validation.
<!-- /section: validator-protocol -->
