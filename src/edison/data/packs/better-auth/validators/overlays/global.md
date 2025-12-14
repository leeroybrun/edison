<!-- extend: tech-stack -->
# Better Auth - Global Validator Overlay

General best practices and validation for all Better Auth implementations across the codebase.

## Guidelines

{{include-section:packs/better-auth/guidelines/includes/better-auth/session-management.md#patterns}}
{{include-section:packs/better-auth/guidelines/includes/better-auth/provider-configuration.md#patterns}}
{{include-section:packs/better-auth/guidelines/includes/better-auth/middleware-patterns.md#patterns}}
{{include-section:packs/better-auth/guidelines/includes/better-auth/client-setup-patterns.md#patterns}}
{{include-section:packs/better-auth/guidelines/includes/better-auth/security-best-practices.md#patterns}}

## Code Quality Standards

- All auth code should be well-documented
- Type safety required (TypeScript strict mode)
- Error handling must be comprehensive
- Tests should cover happy path and error cases

## Documentation Requirements

- Configuration options documented in comments
- Security implications noted for each decision
- Provider-specific notes included
- Examples provided for common use cases

## Testing Requirements

- Unit tests for token validation logic
- Integration tests for middleware
- End-to-end tests for auth flows
- Security tests for vulnerability checks
<!-- /extend -->
