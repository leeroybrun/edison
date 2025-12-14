# Security best practices

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Don’t leak auth details in error messages.
- Rate-limit login endpoints.
- Protect state-changing operations with CSRF mitigations.
- Use HTTPS everywhere; set cookie `Secure` in production.

### Cookie checklist

- `HttpOnly: true`
- `Secure: true` (prod)
- `SameSite: Lax|Strict` as appropriate
<!-- /section: patterns -->
