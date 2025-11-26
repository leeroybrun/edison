# Better Auth Security Best Practices Guidelines

Comprehensive security guidelines for Better Auth implementations.

## Authentication Security

### Credential Storage
- Never store passwords in plaintext
- Use bcrypt or Argon2 for password hashing
- Implement salt rounds >= 10 for bcrypt
- Store hashed passwords securely in database

```typescript
// CORRECT: Use password hashing
import { hash, verify } from 'bcrypt';

const hashedPassword = await hash(plainPassword, 10);
const isValid = await verify(plainPassword, hashedPassword);

// WRONG: Don't do this
const user = { email, password: plainPassword }; // NEVER
```

### Token Security
- Use short-lived access tokens (15-60 minutes)
- Use secure refresh tokens (7-30 days)
- Store refresh tokens in httpOnly cookies
- Validate token signatures on every use
- Implement token rotation on refresh

```typescript
// CORRECT: Token configuration
const auth = await betterAuth({
  sessionConfig: {
    expiresIn: 60 * 60, // 1 hour
    refreshTokenExpiresIn: 7 * 24 * 60 * 60, // 7 days
    cookie: {
      httpOnly: true,
      secure: true,
      sameSite: 'lax',
    },
  },
});
```

## Data Protection

### Sensitive Data Handling
- Never log sensitive data (passwords, tokens, PII)
- Use environment variables for secrets
- Encrypt sensitive data at rest
- Use HTTPS for all data in transit

```typescript
// CORRECT: Protect sensitive data
async function login(email: string, password: string) {
  try {
    // Validate credentials
    const session = await auth.createSession();
    // Log action, not data
    logger.info('User login successful', { userId: user.id });
  } catch (error) {
    // Generic error message
    logger.error('Login attempt failed');
  }
}

// WRONG: Don't log sensitive data
logger.info('Login', { email, password }); // NEVER
```

### PII Protection
- Minimize PII collection
- Get explicit consent for data collection
- Implement data retention policies
- Enable user data deletion
- Hash personal information when possible

## Network Security

### HTTPS Configuration
- Enforce HTTPS in production
- Use modern TLS versions (1.2+)
- Implement HSTS headers
- Keep certificates up to date

```typescript
// CORRECT: Security headers
app.use((req, res, next) => {
  res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Content-Security-Policy', "default-src 'self'");
  next();
});
```

### Cookie Security
- Set httpOnly flag (prevent JavaScript access)
- Set secure flag (HTTPS only)
- Set sameSite attribute (CSRF protection)
- Set appropriate domain and path

```typescript
// CORRECT: Cookie configuration
const auth = await betterAuth({
  sessionConfig: {
    cookie: {
      name: '__auth_session',
      httpOnly: true,
      secure: true, // HTTPS only
      sameSite: 'lax',
      maxAge: 7 * 24 * 60 * 60,
    },
  },
});
```

## Attack Prevention

### CSRF (Cross-Site Request Forgery) Protection
- Use state parameter in OAuth flows
- Implement CSRF tokens for state-changing operations
- Validate origin and referrer headers
- Set SameSite cookie attributes

```typescript
// CORRECT: OAuth state validation
const state = generateRandomString(32);
session.oauth_state = state;

// Verify state on callback
if (callbackState !== session.oauth_state) {
  throw new Error('Invalid OAuth state');
}
```

### XSS (Cross-Site Scripting) Prevention
- Never use dangerouslySetInnerHTML with user data
- Encode user data in responses
- Implement Content Security Policy
- Use httpOnly cookies for sensitive data

### Brute Force Protection
- Implement rate limiting on auth endpoints
- Lock accounts after failed attempts
- Add delays between attempts
- Log suspicious activity

```typescript
// CORRECT: Rate limiting
import rateLimit from 'express-rate-limit';

const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 attempts
  message: 'Too many login attempts',
});

app.post('/api/auth/login', loginLimiter, handleLogin);
```

## Session Security

### Session Fixation Prevention
- Generate new session ID on successful login
- Invalidate old sessions on important changes
- Implement periodic session rotation

```typescript
// CORRECT: Session regeneration
async function handleLogin(user) {
  // Invalidate old session
  await auth.invalidateSession(req.session.id);
  
  // Create new session
  const newSession = await auth.createSession({
    userId: user.id,
  });
}
```

### Session Hijacking Prevention
- Bind sessions to IP address (optional)
- Validate user agent consistency
- Implement device fingerprinting (optional)
- Monitor for suspicious activity

## OAuth/Provider Security

### Provider Integration
- Validate OAuth state parameter
- Verify provider signatures
- Use HTTPS for all provider communications
- Implement provider credential rotation

```typescript
// CORRECT: Provider validation
const profile = await verifyOAuthToken(token, provider.publicKey);
if (!profile) {
  throw new Error('Invalid provider response');
}
```

### Scope Minimization
- Request only necessary scopes
- Document why each scope is needed
- Implement scope upgrade flow for new scopes
- Respect user scope denials

## Authorization Security

### Role-Based Access Control (RBAC)
- Define clear roles and permissions
- Check authorization on every request
- Implement least privilege principle
- Log authorization decisions

```typescript
// CORRECT: Authorization checks
async function deleteUser(userId) {
  // Verify user can delete (is admin or target user)
  const requester = await getCurrentUser();
  
  if (requester.role !== 'admin' && requester.id !== userId) {
    throw new Error('Unauthorized');
  }
  
  // Proceed with deletion
}
```

## Compliance

### GDPR Compliance
- Implement right to deletion
- Get explicit consent for data collection
- Provide data export functionality
- Implement data retention policies

### HIPAA Compliance (Healthcare)
- Encrypt all patient data
- Maintain audit logs
- Implement access controls
- Use secure communication channels

## Monitoring and Logging

### Security Logging
- Log all authentication attempts
- Track failed login attempts
- Monitor unusual activity patterns
- Keep logs for audit trails

```typescript
// CORRECT: Security logging
async function handleLogin(email, password) {
  try {
    const user = await authenticateUser(email, password);
    logger.info('Successful login', {
      userId: user.id,
      timestamp: new Date(),
      ip: req.ip,
    });
  } catch (error) {
    logger.warn('Failed login attempt', {
      email,
      timestamp: new Date(),
      ip: req.ip,
    });
  }
}
```

## Regular Security Practices

- Keep Better Auth updated to latest version
- Use dependency scanning for vulnerabilities
- Implement security headers
- Conduct regular security audits
- Have incident response plan
- Perform penetration testing regularly
