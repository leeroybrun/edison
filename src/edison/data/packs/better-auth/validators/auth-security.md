# Better Auth Security Validator

Security validation rules for Better Auth implementations.

## Session Token Validation

Every authentication must validate tokens server-side on protected endpoints:

```typescript
// CORRECT: Server-side validation
async function protectedRoute(req: Request) {
  const token = req.cookies.get('sessionToken')?.value;
  if (!token) return new Response('Unauthorized', { status: 401 });
  
  const session = await auth.validateSession(token);
  if (!session) return new Response('Unauthorized', { status: 401 });
}

// WRONG: Client-side only validation
if (localStorage.getItem('sessionToken')) {
  // Don't trust client-side state
}
```

## Credential and Secret Management

All credentials must be stored in environment variables:

```typescript
// CORRECT: Use environment variables
const clientId = process.env.OAUTH_CLIENT_ID;
const clientSecret = process.env.OAUTH_CLIENT_SECRET;

// WRONG: Hardcoded credentials
const clientId = 'abc123xyz'; // NEVER
const clientSecret = 'secret456'; // NEVER
```

## Cookie Security Attributes

Session cookies must have proper security attributes:

- httpOnly: true (prevent JavaScript access)
- secure: true (HTTPS only in production)
- sameSite: 'lax' or 'strict' (CSRF protection)
- maxAge/expires: appropriate TTL

```typescript
// CORRECT: Secure cookie configuration
res.setHeader('Set-Cookie', [
  'sessionId=xyz; HttpOnly; Secure; SameSite=Lax; Max-Age=604800',
]);

// WRONG: Missing security attributes
res.setHeader('Set-Cookie', 'sessionId=xyz'); // NEVER
```

## OAuth State Parameter

OAuth callbacks must validate state parameter:

```typescript
// CORRECT: State validation
const state = request.nextUrl.searchParams.get('state');
if (state !== session.oauthState) {
  return new Response('Invalid state', { status: 400 });
}

// WRONG: Missing state validation
// Just accept any callback without state check
```

## Error Message Safety

Authentication errors must not leak information:

```typescript
// CORRECT: Generic error messages
if (!user || !validPassword) {
  return res.status(401).json({ error: 'Invalid credentials' });
}

// WRONG: Leaking information
if (!user) return 'User not found'; // NEVER
if (!validPassword) return 'Invalid password'; // NEVER
```

## Session Expiration

Sessions must have appropriate expiration:

```typescript
// CORRECT: Configure session expiration
const auth = await betterAuth({
  session: {
    expiresIn: 7 * 24 * 60 * 60, // 7 days
  },
});

// WRONG: No expiration
const auth = await betterAuth({
  session: { /* no expires */ },
});
```

## HTTPS Requirement

All authentication endpoints must require HTTPS in production:

```typescript
// CORRECT: Enforce HTTPS
if (process.env.NODE_ENV === 'production') {
  if (!request.headers.get('x-forwarded-proto')?.includes('https')) {
    return new Response('HTTPS required', { status: 403 });
  }
}

// WRONG: Accepting HTTP in production
// No HTTPS enforcement
```

## Database Password Hashing

Passwords must be hashed with strong algorithms:

```typescript
// CORRECT: Strong hashing
import bcrypt from 'bcrypt';
const hash = await bcrypt.hash(password, 10);

// WRONG: Weak or no hashing
const hash = md5(password); // NEVER
storage.password = password; // NEVER
```

## Provider Configuration Validation

OAuth provider configuration must be validated:

```typescript
// CORRECT: Validate provider config
if (!process.env.GOOGLE_CLIENT_ID) {
  throw new Error('GOOGLE_CLIENT_ID is required');
}

const redirectUri = `${process.env.BASE_URL}/auth/google/callback`;
// Verify redirectUri matches provider configuration
```

## CSRF Token Implementation

State-changing operations must use CSRF tokens:

```typescript
// CORRECT: CSRF protection
const csrfToken = generateToken();
session.csrfToken = csrfToken;

// In form submission
if (request.body.csrfToken !== session.csrfToken) {
  return new Response('Invalid CSRF token', { status: 403 });
}

// WRONG: No CSRF protection for state changes
app.post('/logout', handleLogout); // No token check
```

## Rate Limiting

Authentication endpoints must have rate limiting:

```typescript
// CORRECT: Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
});
app.post('/auth/login', limiter, handleLogin);

// WRONG: No rate limiting
app.post('/auth/login', handleLogin); // Vulnerable to brute force
```

## Suspicious Activity Logging

Failed authentication attempts must be logged:

```typescript
// CORRECT: Log suspicious activity
try {
  await authenticateUser(email, password);
} catch (error) {
  logger.warn('Failed login', {
    email,
    ip: request.ip,
    timestamp: new Date(),
  });
}
```

## Session Data Content

Sessions must not contain sensitive information:

```typescript
// CORRECT: Minimal session data
const session = {
  userId: user.id,
  roles: user.roles,
  expiresAt: now + ttl,
};

// WRONG: Sensitive data in session
const session = {
  userId: user.id,
  password: user.password, // NEVER
  apiKey: user.apiKey, // NEVER
};
```

## Provider Credential Rotation

Provider credentials must be rotatable:

```typescript
// CORRECT: Support credential rotation
const auth = await betterAuth({
  providers: [
    google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      // Credentials come from environment, can be rotated
    }),
  ],
});
```

## Content Security Policy

CSP headers must be configured:

```typescript
// CORRECT: CSP configuration
res.setHeader(
  'Content-Security-Policy',
  "default-src 'self'; script-src 'self' 'unsafe-inline'"
);

// WRONG: Missing CSP
// No CSP headers
```

<!-- section: composed-additions -->
<!-- /section: composed-additions -->
