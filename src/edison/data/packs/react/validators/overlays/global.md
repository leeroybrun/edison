# global overlay for React pack

<!-- extend: tech-stack -->
## React Validation Context

### Guidelines
{{include:packs/react/guidelines/react/hooks-patterns.md}}
{{include:packs/react/guidelines/react/component-design.md}}
{{include:packs/react/guidelines/react/server-client-components.md}}
{{include:packs/react/guidelines/react/accessibility.md}}

### Concrete Checks
- Follow Rules of Hooks; no conditional hooks.
- Prefer Server Components; use Client Components for interactivity only.
- Add proper Suspense boundaries and meaningful fallback UI.
- Use `use()` for promise handling where appropriate in React 19.
- Ensure accessible names, roles, and keyboard navigation.
<!-- /extend -->
