# Better Auth Session Management Guidelines

Best practices for managing user sessions in Better Auth implementations.

## Session Storage Strategies

### Database Sessions
**When to use:** Production environments, multi-server deployments, session persistence needs.

```typescript
// Example: Session stored in database
const betterAuth = await initializeBetterAuth({
  sessionStorage: 'database',
  database: dbConnection,
  // ... other config
});
```

**Advantages:**
- Persistent across server restarts
- Scales across multiple servers
- Enables session querying and management
- Better for compliance and auditing

**Disadvantages:**
- Database query overhead
- Requires database schema management

### In-Memory Sessions
**When to use:** Development, single-server deployments, temporary sessions.

```typescript
// Example: In-memory session storage
const betterAuth = await initializeBetterAuth({
  sessionStorage: 'memory',
  // ... other config
});
```

**Advantages:**
- Fast session access
- No database overhead
- Simple to set up

**Disadvantages:**
- Sessions lost on server restart
- Cannot scale across multiple servers
- Not suitable for production

## Session Lifecycle Management

### Creating Sessions
```typescript
// Sessions should be created after successful authentication
const session = await auth.createSession({
  userId: user.id,
  expiresIn: 7 * 24 * 60 * 60, // 7 days
  // ... other options
});
```

### Session Validation
```typescript
// Always validate sessions on protected routes
async function protectedRoute(req, res) {
  const session = await auth.validateSession(req.cookies.sessionId);
  
  if (!session || session.expired) {
    return res.status(401).json({ error: 'Invalid session' });
  }
  
  // Process request with session
}
```

### Session Refresh
```typescript
// Refresh sessions before expiration
if (session.expiresIn < 1 * 24 * 60 * 60) {
  const newSession = await auth.refreshSession(session.id);
}
```

### Session Cleanup
```typescript
// Explicitly invalidate sessions on logout
async function logout(req, res) {
  await auth.invalidateSession(req.session.id);
  res.clearCookie('sessionId');
}
```

## Session Configuration Best Practices

### Expiration Times
- Short-lived sessions (15-30 minutes): High-security operations
- Medium-lived sessions (2-8 hours): Standard web applications
- Long-lived sessions (7-30 days): "Remember me" functionality

### Session Data
- Store minimal data in sessions (user ID, roles)
- Load additional user data from database as needed
- Never store passwords or sensitive tokens
- Keep session payload under 4KB

### Session Storage
```typescript
// Example: Configuring session storage
const betterAuth = await initializeBetterAuth({
  sessionConfig: {
    expiresIn: 7 * 24 * 60 * 60,
    updateAge: 24 * 60 * 60, // Update expiry on activity
    absoluteTimeout: 30 * 24 * 60 * 60, // Force re-auth after 30 days
    sameSite: 'lax',
    secure: true, // HTTPS only
    httpOnly: true, // No JavaScript access
  },
});
```

## Anti-Patterns

- Using client-side session storage (LocalStorage/SessionStorage only)
- Not validating sessions on every protected request
- Setting excessively long session durations
- Storing sensitive data in session cookies
- Not implementing session cleanup schedules
- Trusting client-side session state without server validation
