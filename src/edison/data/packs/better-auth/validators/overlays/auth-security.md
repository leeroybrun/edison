<!-- EXTEND: composed-additions -->
# Better Auth Security Validation - Overlay

Security validation rules for Better Auth implementations to ensure safe authentication and authorization practices.

## Critical Security Checks

### 1. Token Validation
- [ ] Tokens must be verified server-side on every protected request
- [ ] Token expiration must be validated
- [ ] Token signatures must match expected algorithm
- [ ] Token claims must be verified for authenticity
- [ ] Refresh tokens must be stored securely (httpOnly cookies)

### 2. Environment & Secrets
- [ ] All OAuth/provider credentials in environment variables
- [ ] No secrets hardcoded in source files
- [ ] Environment files not committed to version control
- [ ] Separate dev/staging/production credentials
- [ ] Secrets rotation policy documented

### 3. Session Security
- [ ] Session storage is configured securely
- [ ] Session IDs are cryptographically random
- [ ] Sessions have appropriate TTL/expiration
- [ ] Expired sessions are properly cleaned up
- [ ] Session data doesn't contain sensitive information

### 4. CSRF/XSRF Protection
- [ ] CSRF tokens generated for state-changing operations
- [ ] CSRF tokens validated on server
- [ ] SameSite cookie attributes configured
- [ ] State parameter used in OAuth flows

### 5. OAuth/Provider Configuration
- [ ] Redirect URIs match provider configuration exactly
- [ ] OAuth state parameter validates callback
- [ ] Provider credentials never exposed to client
- [ ] Callback handlers validate responses

### 6. Error Handling
- [ ] Error messages don't leak authentication details
- [ ] Generic error messages for failed auth attempts
- [ ] Errors logged for debugging but not exposed
- [ ] Rate limiting prevents brute force attacks

### 7. HTTPS & Transport
- [ ] All auth endpoints require HTTPS
- [ ] Secure flag set on cookies
- [ ] HttpOnly flag set on sensitive cookies
- [ ] Content Security Policy headers configured
- [ ] X-Frame-Options header set to DENY

### 8. Authorization Checks
- [ ] Protected routes validate user authorization
- [ ] User roles/permissions properly checked
- [ ] Resource ownership verified before access
- [ ] Authorization logic centralized and tested
<!-- /EXTEND -->
