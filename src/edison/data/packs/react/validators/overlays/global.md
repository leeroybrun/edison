# global overlay for React pack

<!-- extend: tech-stack -->
## React Validation Context

### Guidelines
{{include-section:packs/react/guidelines/includes/react/hooks-patterns.md#patterns}}
{{include-section:packs/react/guidelines/includes/react/component-design.md#patterns}}
{{include-section:packs/react/guidelines/includes/react/server-client-components.md#patterns}}
{{include-section:packs/react/guidelines/includes/react/accessibility.md#patterns}}

### Concrete Checks
- Follow Rules of Hooks; no conditional hooks.
- Prefer Server Components; use Client Components for interactivity only.
- Add proper Suspense boundaries and meaningful fallback UI.
- Use `use()` for promise handling where appropriate in React 19.
- Ensure accessible names, roles, and keyboard navigation.
<!-- /extend -->
