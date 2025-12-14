# Middleware

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Keep middleware **small** and **edge-compatible**.
- Scope aggressively with `config.matcher`; avoid running on `_next` assets.
- Avoid project-specific routes; use placeholders.

### Minimal illustrative pattern

```ts
import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token')
  const isProtected = request.nextUrl.pathname.startsWith('<protected-prefix>')

  if (isProtected && !token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
```
<!-- /section: patterns -->
