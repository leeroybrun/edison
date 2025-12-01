# Server vs Client Components

- Prefer Server Components by default for static and data-driven UI.
- Use Client Components only for interactivity (events, stateful UI, browser APIs).
- Minimize Client Component boundaries; pass serializable props.
- Avoid unnecessary `useEffect`; prefer data fetching on the server.
- In React 19 with Server Components and Server Actions, treat server actions as first-class endpoints and avoid client-only data fetching when a server action is viable.
