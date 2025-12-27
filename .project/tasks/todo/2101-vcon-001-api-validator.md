<!-- TaskID: 2101-vcon-001-api-validator -->
<!-- Priority: 2101 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: feature -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave2-groupA -->
<!-- EstimatedHours: 4 -->
<!-- DependsOn: 2003-efix-003, 2004-efix-004 -->

# VCON-001: Create api.md Validator Constitution

## Summary
Create a complete API validator constitution based on the OLD system's 694-line api.md validator. This specialized validator checks API endpoint implementations for correctness, security, and best practices.

## Problem Statement
The OLD system had a comprehensive api.md validator (694 lines) that is MISSING from Edison. This validator enforced:
- REST conventions
- Authentication patterns
- Error handling standards
- Response format compliance
- Rate limiting verification

## Dependencies
- EFIX-003 (rules composition) - helpful but not blocking
- EFIX-004 (AGENTS.md generator) - helpful but not blocking

## Objectives
- [x] Create complete api.md validator
- [x] Include all validation rules from OLD system
- [x] Add Wilson-specific API patterns
- [x] Ensure composability (core + overlay structure)

## Source Files

### Reference - Old Validator
```
/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/specialized/api.md
```

### Wilson Overlay Reference
```
/Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/validators/api.md
```

### Output Location
```
/Users/leeroy/Documents/Development/edison/src/edison/data/validators/specialized/api.md
```

## Precise Instructions

### Step 1: Analyze Old Validator
```bash
cat /Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/specialized/api.md | head -100
wc -l /Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/specialized/api.md
# Expected: ~694 lines
```

### Step 2: Identify Core vs Project-Specific Content

**Core (technology-agnostic) content** - goes to Edison:
- REST convention rules
- HTTP status code validation
- Error response format rules
- Authentication verification patterns
- Rate limiting checks
- API versioning rules

**Project-specific content** - stays in Wilson overlay:
- Wilson API path patterns (`/api/v1/dashboard/*`)
- Better-Auth integration checks
- Fastify-specific patterns
- Wilson response envelope format

### Step 3: Create Edison Core Validator

Create `/Users/leeroy/Documents/Development/edison/src/edison/data/validators/specialized/api.md`:

```markdown
---
id: api
type: specialized
model: codex
triggers:
  - "**/api/**/*.ts"
  - "**/route.ts"
  - "**/routes/**/*.ts"
blocksOnFail: false
---

# API Validator

**Type**: Specialized Validator
**Triggers**: API route files
**Blocking**: No (advisory)

## Constitution Awareness

**Role Type**: VALIDATOR
**Constitution**: `.edison/_generated/constitutions/VALIDATORS.md`

### Binding Rules
1. **Re-read Constitution**: At validation start and after context compaction
2. **Authority**: Constitution > Validator Guidelines > Task Context
3. **Role Boundaries**: You VALIDATE API implementations. You do NOT implement fixes.
4. **Output**: APPROVED, APPROVED_WITH_WARNINGS, or REJECTED with evidence

## Validation Scope

This validator checks API endpoint implementations for:
1. REST convention compliance
2. HTTP method correctness
3. Status code appropriateness
4. Error handling completeness
5. Authentication/authorization patterns
6. Response format consistency
7. Input validation presence

## Validation Rules

### VR-API-001: HTTP Method Semantics
**Severity**: Error
**Check**: HTTP methods match operation semantics

| Method | Allowed Operations |
|--------|-------------------|
| GET | Read-only, idempotent, no request body |
| POST | Create resource, non-idempotent |
| PUT | Full update, idempotent |
| PATCH | Partial update |
| DELETE | Remove resource, idempotent |

**Fail Condition**: Method doesn't match operation (e.g., GET with side effects)

### VR-API-002: Status Code Accuracy
**Severity**: Error
**Check**: Response status codes match outcomes

| Outcome | Expected Code(s) |
|---------|------------------|
| Success (read) | 200 |
| Success (create) | 201 |
| Success (no content) | 204 |
| Client error (bad input) | 400 |
| Unauthorized | 401 |
| Forbidden | 403 |
| Not found | 404 |
| Conflict | 409 |
| Server error | 500 |

**Fail Condition**: Wrong status code for outcome

### VR-API-003: Error Response Format
**Severity**: Warning
**Check**: Error responses follow consistent format

Expected structure:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {} // optional
  }
}
```

**Fail Condition**: Inconsistent error format

### VR-API-004: Input Validation
**Severity**: Error
**Check**: All user inputs are validated before use

Required validations:
- Request body schema validation (Zod recommended)
- Query parameter type checking
- Path parameter format validation
- Header value validation (where applicable)

**Fail Condition**: User input used without validation

### VR-API-005: Authentication Check
**Severity**: Error
**Check**: Protected endpoints verify authentication

Patterns to verify:
- Auth middleware applied to protected routes
- Token/session validation before data access
- Proper 401 response for missing auth
- Proper 403 response for insufficient permissions

**Fail Condition**: Protected data accessible without auth

### VR-API-006: Authorization Check
**Severity**: Error
**Check**: Resource access is authorized

Patterns to verify:
- User can only access own resources (unless admin)
- Role-based access control applied
- Resource ownership verified before mutation

**Fail Condition**: Cross-user data access possible

### VR-API-007: Rate Limiting
**Severity**: Warning
**Check**: Endpoints have rate limiting

Verify:
- Rate limit headers present (X-RateLimit-*)
- 429 response when limit exceeded
- Reasonable limits for endpoint type

**Fail Condition**: No rate limiting on public endpoints

### VR-API-008: API Versioning
**Severity**: Info
**Check**: API version is explicit

Patterns:
- URL path versioning (`/api/v1/...`)
- Header versioning (`Accept-Version: v1`)
- Clear deprecation warnings for old versions

**Fail Condition**: No versioning strategy

### VR-API-009: Request/Response Logging
**Severity**: Warning
**Check**: API calls are logged for debugging

Required logging:
- Request method and path
- Response status code
- Request duration
- Error details (sanitized)

**Fail Condition**: No request logging

### VR-API-010: Sensitive Data Protection
**Severity**: Error
**Check**: Sensitive data not exposed in responses

Never return:
- Passwords or hashes
- Internal IDs (use UUIDs)
- Full stack traces in production
- Database connection details

**Fail Condition**: Sensitive data in response

## Validation Workflow

1. **Identify Endpoints**: Find all route handlers in changed files
2. **Check Each Rule**: Apply VR-API-001 through VR-API-010
3. **Collect Evidence**: Record specific code locations
4. **Generate Report**: Produce JSON + Markdown output

## Output Format

```json
{
  "validator": "api",
  "status": "APPROVED" | "APPROVED_WITH_WARNINGS" | "REJECTED",
  "filesChecked": ["path/to/route.ts"],
  "findings": [
    {
      "rule": "VR-API-001",
      "severity": "error",
      "file": "path/to/route.ts",
      "line": 42,
      "message": "GET endpoint has side effects",
      "suggestion": "Use POST for operations with side effects"
    }
  ],
  "summary": {
    "errors": 0,
    "warnings": 0,
    "info": 0
  }
}
```

## Context7 Requirements

Before validating, refresh knowledge on:
- Current API framework patterns (Fastify/Express/Next.js)
- HTTP specification details
- Security best practices

```
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: "/fastify/fastify",
  topic: "routes"
})
```
```

### Step 4: Verify Wilson Overlay Exists
```bash
cat /Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/validators/api.md | head -50
```

If overlay doesn't exist or is incomplete, create Wilson-specific additions:

```markdown
# Wilson API Validator Overlay

## Additional Rules

### VR-API-W01: Wilson Response Envelope
**Severity**: Error
**Check**: Responses use Wilson envelope format

Expected:
```json
{
  "data": { ... },
  "error": null
}
// OR
{
  "data": null,
  "error": { "code": "...", "message": "..." }
}
```

### VR-API-W02: Better-Auth Integration
**Severity**: Error
**Check**: Authentication uses Better-Auth patterns

Verify:
- `getSessionFromRequest()` used correctly
- Role extraction from session
- Proper session validation

### VR-API-W03: Wilson API Paths
**Severity**: Warning
**Check**: API paths follow Wilson conventions

Pattern: `/api/v1/dashboard/{resource}/{id?}/{action?}`
```

### Step 5: Test Composition
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen
edison compose validators

# Verify output
wc -l .edison/_generated/validators/specialized/api.md
# Should be substantial (400+ lines after composition)
```

## Verification Checklist
- [ ] Core validator created at Edison path
- [ ] Contains all 10 VR-API rules
- [ ] Wilson overlay exists with project-specific rules
- [ ] Composition produces complete validator
- [ ] Output includes both core and overlay rules
- [ ] JSON output format documented
- [ ] Context7 requirements specified

## Success Criteria
A complete API validator exists that combines Edison core rules with Wilson-specific patterns, producing comprehensive API validation.

## Related Issues
- Audit ID: Wave 5 validator findings
- Audit ID: ~3,400 lines missing validator content
