# test-engineer overlay for Vitest pack

<!-- extend: tools -->
- Vitest for unit/integration tests; config in `vitest.config.*`.
- React Testing Library for components; Playwright for E2E where applicable.
- Coverage: run your project's test command with coverage enabled (project-script / CI command).
- Test utilities: use your project's shared test helpers/fixtures (avoid hardcoded import aliases and paths).
<!-- /extend -->

<!-- extend: guidelines -->
- Write failing tests first (TDD) covering happy path, edge cases, and regression risks; avoid brittle stubbing.
- Prefer RTL queries by role/text/label; avoid test IDs unless necessary.
- Keep tests isolated and parallel-safe; clean up DOM/state between runs.
- For Playwright, record evidence (screenshots/logs) and keep selectors resilient.
- Avoid mocking internal modules (DB/ORM, auth, business logic). Prefer real dependencies and boundary-only test doubles when unavoidable.
<!-- /extend -->

<!-- section: VitestPatterns -->
## Vitest Tech Stack
- **Vitest**: Unit + integration tests
- **React Testing Library**: Component tests
- **Playwright**: E2E tests

## Vitest Test Structure
```typescript
import { describe, it, expect, beforeEach, afterAll } from 'vitest'

describe('Feature Name', () => {
  beforeEach(() => {
    // Setup before each test
  })

  afterAll(async () => {
    // Cleanup after all tests in suite
  })

  it('should do something specific', async () => {
    // Arrange
    // Act
    // Assert
    expect(result).toBe(expected)
  })
})
```

## Vitest Coverage Configuration
```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'test/',
        '**/*.d.ts',
        '**/*.test.ts',
        '**/*.spec.ts',
      ],
      thresholds: {
        statements: 80,
        branches: 80,
        functions: 80,
        lines: 80,
      },
    },
  },
})
```

## Boundary Stubbing (Only When Unavoidable)
If an external third-party boundary cannot be exercised in tests (rate limits, costs, nondeterminism), stub **only** that boundary and keep all internal modules real.

## React Testing Library Patterns
```typescript
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

it('renders and handles interaction', async () => {
  const user = userEvent.setup()

  render(<MyComponent />)

  // Query by role (preferred)
  const button = screen.getByRole('button', { name: /submit/i })

  // Query by text
  const heading = screen.getByText(/welcome/i)

  // Query by label
  const input = screen.getByLabelText(/email/i)

  // User interaction
  await user.click(button)
  await user.type(input, 'test@example.com')

  // Wait for async updates
  await waitFor(() => {
    expect(screen.getByText(/success/i)).toBeInTheDocument()
  })
})
```

## Playwright E2E Patterns
```typescript
import { test, expect } from '@playwright/test'

test('user flow works end to end', async ({ page }) => {
  await page.goto('/dashboard')

  // Wait for page to load
  await page.waitForSelector('[data-testid="dashboard-loaded"]')

  // Interact with elements
  await page.click('button:has-text("Create")')
  await page.fill('input[name="title"]', 'New Item')
  await page.click('button[type="submit"]')

  // Assert results
  await expect(page.locator('.success-message')).toBeVisible()

  // Screenshot evidence
  await page.screenshot({ path: 'evidence/user-flow-complete.png' })
})
```

## Vitest Performance Targets
- Unit tests: <100ms each
- Component tests: <200ms each
- Integration tests: <1s each
- API route tests: ~35-50ms each

## Vitest Commands
```bash
# Run all tests (use your configured test command)
<test-command>

# Run with coverage (use your configured coverage flags)
<test-command> -- --coverage

# Run in watch mode
<test-command> -- --watch

# Run specific test by name
<test-command> -- -t "should filter by status"

# Run with verbose output
<test-command> -- --reporter=verbose
```
<!-- /section: VitestPatterns -->





