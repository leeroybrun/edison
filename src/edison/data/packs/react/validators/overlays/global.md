# global overlay for React pack

<!-- EXTEND: TechStack -->
## React Validation Context

### Guidelines
{{include:.edison/_generated/guidelines/react/hooks-patterns.md}}
{{include:.edison/_generated/guidelines/react/component-design.md}}
{{include:.edison/_generated/guidelines/react/server-client-components.md}}
{{include:.edison/_generated/guidelines/react/accessibility.md}}

### Concrete Checks
- Follow Rules of Hooks; no conditional hooks.
- Prefer Server Components; use Client Components for interactivity only.
- Add proper Suspense boundaries and meaningful fallback UI.
- Use `use()` for promise handling where appropriate in React 19.
- Ensure accessible names, roles, and keyboard navigation.
<!-- /EXTEND -->
