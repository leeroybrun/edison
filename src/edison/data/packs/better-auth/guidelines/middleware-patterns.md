# Better Auth Middleware Patterns Guidelines

Best practices for implementing authentication middleware with Better Auth.

## Middleware Architecture

### Next.js Middleware Pattern
```typescript
// middleware.ts - Global authentication middleware
import { betterAuth } from '@/lib/auth';
import { NextRequest, NextResponse } from 'next/server';

const protectedRoutes = ['/dashboard', '/settings', '/api/protected'];
const authRoutes = ['/login', '/register', '/auth'];

export async function middleware(request: NextRequest) {
  const session = await betterAuth.api.getSession({
    headers: request.headers,
  });

  const isProtectedRoute = protectedRoutes.some(route =>
    request.nextUrl.pathname.startsWith(route)
  );

  // Redirect unauthenticated users away from protected routes
  if (isProtectedRoute && !session) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('from', request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Redirect authenticated users away from auth routes
  if (authRoutes.some(route => request.nextUrl.pathname.startsWith(route)) && session) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
```

### Express.js Middleware Pattern
```typescript
import { betterAuth } from './auth';
import { Request, Response, NextFunction } from 'express';

// Authentication middleware
async function authenticateUser(req: Request, res: Response, next: NextFunction) {
  try {
    const session = await betterAuth.api.getSession({
      headers: req.headers,
    });

    if (!session) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    // Attach session to request for downstream handlers
    (req as any).session = session;
    (req as any).user = session.user;
    next();
  } catch (error) {
    res.status(500).json({ error: 'Authentication failed' });
  }
}

// Role-based authorization middleware
function authorize(...requiredRoles: string[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    const userRole = (req as any).session?.user?.role;

    if (!requiredRoles.includes(userRole)) {
      return res.status(403).json({ error: 'Forbidden' });
    }

    next();
  };
}

// Usage
app.get('/api/admin', authenticateUser, authorize('admin'), (req, res) => {
  res.json({ message: 'Admin only' });
});
```

## Session Validation Patterns

### Request-Level Session Validation
```typescript
// Validate session on every protected request
async function getSessionFromRequest(req: Request) {
  const session = await betterAuth.api.getSession({
    headers: req.headers,
  });

  if (!session || session.expired) {
    throw new Error('Invalid or expired session');
  }

  return session;
}
```

### Context Propagation
```typescript
// Propagate session through request context
import { createContext } from 'react';

export const SessionContext = createContext<Session | null>(null);

// Server component
export async function SessionProvider({ children }) {
  const session = await auth.api.getSession();

  return (
    <SessionContext.Provider value={session}>
      {children}
    </SessionContext.Provider>
  );
}

// Client component
import { useContext } from 'react';

export function useSession() {
  const session = useContext(SessionContext);
  if (!session) throw new Error('useSession must be used within SessionProvider');
  return session;
}
```

## Error Handling in Middleware

```typescript
// Comprehensive error handling
async function authMiddleware(req: Request, res: Response, next: NextFunction) {
  try {
    const session = await betterAuth.api.getSession({
      headers: req.headers,
    });

    if (!session) {
      return res.status(401).json({
        error: 'Unauthorized',
        code: 'NO_SESSION',
      });
    }

    (req as any).session = session;
    next();
  } catch (error) {
    if (error.code === 'INVALID_TOKEN') {
      return res.status(401).json({ error: 'Invalid session token' });
    }

    if (error.code === 'EXPIRED_SESSION') {
      return res.status(401).json({ error: 'Session expired' });
    }

    // Generic error - don't leak details
    console.error('Auth middleware error:', error);
    return res.status(500).json({ error: 'Authentication failed' });
  }
}
```

## Ordering and Composition

```typescript
// Middleware execution order matters
const app = express();

// 1. Parse request body
app.use(express.json());

// 2. Session validation
app.use(authMiddleware);

// 3. Logging and tracking
app.use(loggingMiddleware);

// 4. Route handlers
app.get('/api/protected', handleRequest);
```

## Anti-Patterns

- Validating sessions only on some requests
- Storing sensitive data in middleware context
- Not handling session expiration gracefully
- Missing error handling in middleware
- Middleware ordering that validates before parsing
- Using multiple conflicting authentication strategies
