# Hooks Patterns

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Only call hooks at the top level of components or custom hooks.
- Derive state; avoid redundant `useState` when values can be computed.
- Memoize expensive calculations with `useMemo`; keep dependencies minimal and explicit.
- Use `useCallback` to stabilize function props when needed.
<!-- /section: patterns -->

