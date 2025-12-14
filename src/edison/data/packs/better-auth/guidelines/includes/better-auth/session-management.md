# Session management

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Store sessions in a **server-validated** mechanism (signed/opaque id), not client-trusted claims.
- Set cookie flags: `HttpOnly`, `Secure` (in prod), and appropriate `SameSite`.
- Enforce expiry/TTL server-side and handle rotation.

### Checks

- Session read on every protected request.
- Logout invalidates server session.
- No sensitive data stored in session payload.
<!-- /section: patterns -->
