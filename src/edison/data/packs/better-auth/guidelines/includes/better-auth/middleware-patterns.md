# Middleware patterns

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Keep middleware **fast** and **edge-compatible**.
- Avoid provider calls in middleware; only do cheap session presence checks.
- Avoid hardcoded app routes; use placeholders.

```ts
const isProtected = request.nextUrl.pathname.startsWith('<protected-prefix>')
if (isProtected && !hasSessionCookie) {
  return NextResponse.redirect(new URL('/login', request.url))
}
```
<!-- /section: patterns -->
