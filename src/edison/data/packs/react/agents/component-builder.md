# component-builder-react (React 19)

## Tools
- React 19 with strict TypeScript; hooks/components in `apps/dashboard/src/**`.
- Testing with Vitest/RTL via `pnpm test --filter dashboard`.

## Guidelines
- Favor composition and pure components; avoid side effects in render paths.
- Use `use`/Server Components patterns when inside Next.js, otherwise standard client components with suspense-ready data flows.
- Keep props typed, stable, and documented; lift shared state; memoize where performance matters.
- Ensure accessibility (labels, focus, keyboard) and responsive layouts aligned to design system.
