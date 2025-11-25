# test-engineer-vitest (Vitest / RTL / Playwright)

## Tools
- Vitest for unit/integration tests; config in `vitest.config.*`.
- React Testing Library for components; Playwright for E2E where applicable.
- Coverage commands: `pnpm test --filter dashboard -- --coverage`.

## Guidelines
- Write failing tests first (TDD) covering happy path, edge cases, and regression risks; avoid brittle mocks.
- Prefer RTL queries by role/text/label; avoid test IDs unless necessary.
- Keep tests isolated and parallel-safe; reset modules/mocks and clean up DOM between runs.
- For Playwright, record evidence (screenshots/logs) and keep selectors resilient.
