# Next.js 16 Middleware Guidelines

This document outlines the standard patterns and best practices for implementing Middleware in Next.js 16 applications within the Edison ecosystem.

## Overview

**Middleware** allows you to run code before a request is completed. Then, based on the incoming request, you can modify the response by rewriting, redirecting, modifying the request or response headers, or responding directly.

Middleware runs before cached content and routes are matched.

## File Location and Convention

- **File Name:** `middleware.ts` (or `middleware.js`)
- **Location:** Must be placed in the root of your project (at the same level as `pages` or `app`, or inside `src` if applicable).
- **Export:** Must export a function named `middleware`.

## Standard Structure

Middleware relies on `NextRequest` and `NextResponse` objects.

```typescript
// middleware.ts
import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  // Logic goes here
  return NextResponse.next()
}
```

## Configuration: Matcher

The `matcher` allows you to filter Middleware to run on specific paths.

```typescript
export const config = {
  // Match all request paths except for the ones starting with:
  // - api (API routes)
  // - _next/static (static files)
  // - _next/image (image optimization files)
  // - favicon.ico (favicon file)
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
```

## Common Patterns

### 1. Authentication

Verify user sessions or tokens before allowing access to protected routes.

```typescript
import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  // Assume 'auth_token' is the name of your session cookie
  const token = request.cookies.get('auth_token')

  // Define protected routes
  const isProtectedRoute = request.nextUrl.pathname.startsWith('/dashboard')

  if (isProtectedRoute && !token) {
    // Redirect unauthenticated users to login
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}
```

### 2. Redirects and Rewrites

Conditional routing based on request properties (e.g., geolocation, feature flags).

```typescript
import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  const url = request.nextUrl

  // Legacy path redirect
  if (url.pathname === '/old-blog') {
    url.pathname = '/blog'
    return NextResponse.redirect(url)
  }

  // Rewrite for internal handling (URL in browser doesn't change)
  if (url.pathname.startsWith('/store')) {
    url.pathname = '/commerce/store'
    return NextResponse.rewrite(url)
  }

  return NextResponse.next()
}
```

### 3. Header Manipulation

Add custom headers for downstream processing or security.

```typescript
import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-custom-header', 'edison-middleware')

  // You can also set request headers in NextResponse.next
  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  })

  // Set a new response header `x-hello-from-middleware`
  response.headers.set('x-hello-from-middleware', 'hello')
  return response
}
```

## Edge Runtime Considerations

Middleware currently runs in the [Edge Runtime](https://nextjs.org/docs/app/building-your-application/rendering/edge-and-nodejs-runtimes).
- **Limitations:** Native Node.js APIs are not supported (e.g., reading from the filesystem directly).
- **Performance:** Logic must be lightweight to ensure low latency.
- **Dependencies:** Ensure imported libraries are Edge-compatible.

## Complete Example

Here is a comprehensive example combining auth checks and header handling.

```typescript
// middleware.ts
import { NextRequest, NextResponse } from 'next/server'

const PUBLIC_FILE = /\.(.*)$/

export async function middleware(req: NextRequest) {
  // 1. Skip public files and static assets
  if (
    req.nextUrl.pathname.startsWith('/_next') ||
    req.nextUrl.pathname.includes('/api/') ||
    PUBLIC_FILE.test(req.nextUrl.pathname)
  ) {
    return
  }

  // 2. Authentication Check
  const token = req.cookies.get('token')
  const isDashboard = req.nextUrl.pathname.startsWith('/dashboard')

  if (isDashboard && !token) {
    const loginUrl = new URL('/login', req.url)
    // Store the original url to redirect back after login
    loginUrl.searchParams.set('from', req.nextUrl.pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
```
