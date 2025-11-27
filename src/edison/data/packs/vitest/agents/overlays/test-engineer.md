# test-engineer overlay for Vitest pack

<!-- EXTEND: Tools -->
- Vitest for unit/integration tests; config in `vitest.config.*`.
- React Testing Library for components; Playwright for E2E where applicable.
- Coverage commands: `pnpm test --filter dashboard -- --coverage`.
- Test utilities: `@/test/auth-helpers`, `@/test/db/template-pool`, `@/test/db`.
<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->
- Write failing tests first (TDD) covering happy path, edge cases, and regression risks; avoid brittle mocks.
- Prefer RTL queries by role/text/label; avoid test IDs unless necessary.
- Keep tests isolated and parallel-safe; reset modules/mocks and clean up DOM between runs.
- For Playwright, record evidence (screenshots/logs) and keep selectors resilient.
- Use `vi.mock()` only for external APIs, never for internal modules (ORM, auth).
- Use `vi.spyOn()` to observe behavior without replacing implementation.
- Clean up mocks between tests with `vi.clearAllMocks()` or `vi.resetAllMocks()`.
<!-- /EXTEND -->

<!-- NEW_SECTION: VitestPatterns -->
## Vitest Tech Stack
- **Vitest**: Unit + integration tests
- **React Testing Library**: Component tests
- **Playwright**: E2E tests
- **MSW** (Mock Service Worker): External API mocking

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

## Vitest Mocking Patterns
```typescript
import { vi, describe, it, expect } from 'vitest'

// Mock external modules only
vi.mock('external-api-client', () => ({
  fetchData: vi.fn(),
}))

// Mock timers for time-dependent tests
vi.useFakeTimers()
vi.advanceTimersByTime(1000)
vi.useRealTimers()

// Spy on functions
const spy = vi.spyOn(object, 'method')
expect(spy).toHaveBeenCalledWith(expectedArgs)
```

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
# Run all tests
pnpm test

# Run specific test file
pnpm test path/to/test.ts

# Run with coverage
pnpm test -- --coverage

# Run in watch mode
pnpm test -- --watch

# Run specific test by name
pnpm test -- -t "should filter by status"

# Run with verbose output
pnpm test -- --reporter=verbose
```
<!-- /NEW_SECTION -->




