# Route Handlers (API)

- Implement handlers in `app/api/<version>/<resource>/route.ts`.
- Validate inputs at the boundary; return typed JSON responses.
- Use appropriate status codes; avoid leaking internals in errors.
- Keep handler thin; delegate business logic to modules.

