<!-- TaskID: 2103-vcon-003-nextjs-validator -->
<!-- Priority: 2103 -->
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
<!-- EstimatedHours: 3 -->

# VCON-003: Create nextjs.md Validator Constitution

## Summary
Create a complete Next.js validator constitution based on the OLD system's ~700-line nextjs.md validator. This specialized validator checks Next.js App Router patterns, server components, and routing best practices.

## Problem Statement
The OLD system had a comprehensive nextjs.md validator (~700 lines) that is MISSING from Edison core. The validation rules are well-modularized in the nextjs pack guidelines but need a unified validator.

## Dependencies
- None - can work with existing pack guidelines

## Objectives
- [x] Create complete nextjs.md validator
- [x] Integrate with nextjs pack guidelines
- [x] Cover App Router, server components, caching
- [x] Ensure composability

## Source Files

### Reference - Old Validator
```
/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/specialized/nextjs.md
```

### Pack Guidelines
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/nextjs/guidelines/
```

### Output Location
```
/Users/leeroy/Documents/Development/edison/src/edison/data/validators/specialized/nextjs.md
```

## Precise Instructions

### Step 1: Analyze Old Validator
```bash
wc -l /Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/specialized/nextjs.md
cat /Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/specialized/nextjs.md | head -100
```

### Step 2: Review Pack Guidelines
```bash
ls /Users/leeroy/Documents/Development/edison/src/edison/packs/nextjs/guidelines/
```

### Step 3: Create Validator

Create `/Users/leeroy/Documents/Development/edison/src/edison/data/validators/specialized/nextjs.md`:

```markdown
---
id: nextjs
type: specialized
model: codex
triggers:
  - "app/**/*.tsx"
  - "**/route.ts"
  - "**/layout.tsx"
  - "**/page.tsx"
  - "**/loading.tsx"
  - "**/error.tsx"
blocksOnFail: false
---

# Next.js Validator

**Type**: Specialized Validator
**Triggers**: Next.js App Router files
**Blocking**: No (advisory)

## Constitution Awareness

**Role Type**: VALIDATOR
**Constitution**: `.edison/_generated/constitutions/VALIDATORS.md`

## Validation Scope

This validator checks Next.js implementations for:
1. App Router conventions
2. Server/Client component boundaries
3. Routing best practices
4. Metadata configuration
5. Loading/Error states
6. Caching strategies
7. Data fetching patterns

## Validation Rules

### VR-NEXT-001: Server Component Default
**Severity**: Warning
**Check**: Components are Server Components unless marked otherwise

Verify:
- No unnecessary "use client" directives
- Client components are properly marked
- Server-only code not in client components

**Fail Condition**: "use client" without client-specific features

### VR-NEXT-002: Client Component Justification
**Severity**: Info
**Check**: "use client" is justified

Valid reasons for client:
- useState, useEffect, useContext
- Event handlers (onClick, onChange)
- Browser APIs (localStorage, window)
- Third-party client-only libraries

**Fail Condition**: "use client" without valid reason

### VR-NEXT-003: Route Handler Conventions
**Severity**: Error
**Check**: Route handlers follow conventions

Verify:
- Only exported GET, POST, PUT, PATCH, DELETE
- Named exports, not default
- Proper Request/Response types
- No mixing with page.tsx

**Fail Condition**: Invalid route handler exports

### VR-NEXT-004: Layout Usage
**Severity**: Warning
**Check**: Layouts are used appropriately

Verify:
- Shared UI in layouts, not duplicated
- No state in layouts (they persist)
- Proper nesting hierarchy
- RootLayout has html/body

**Fail Condition**: Layout anti-patterns

### VR-NEXT-005: Metadata Export
**Severity**: Warning
**Check**: Pages export metadata

Verify:
- metadata or generateMetadata exported
- Title and description present
- OpenGraph data for public pages

**Fail Condition**: Missing metadata on pages

### VR-NEXT-006: Loading States
**Severity**: Info
**Check**: Async pages have loading states

Verify:
- loading.tsx exists for async pages
- Or Suspense boundaries in page
- Skeleton UI matches content

**Fail Condition**: Async page without loading state

### VR-NEXT-007: Error Boundaries
**Severity**: Warning
**Check**: Error handling is configured

Verify:
- error.tsx exists at appropriate levels
- "use client" directive present
- Reset function provided
- User-friendly messages

**Fail Condition**: No error handling

### VR-NEXT-008: Data Fetching Patterns
**Severity**: Warning
**Check**: Data fetching follows patterns

Patterns to verify:
- Server Components fetch directly
- Client Components use hooks
- No fetch in Client Components (prefer server)
- Proper cache/revalidate options

**Fail Condition**: Client-side fetch for server data

### VR-NEXT-009: Dynamic Routes
**Severity**: Info
**Check**: Dynamic routes are correct

Verify:
- [param] naming correct
- generateStaticParams for static generation
- Catch-all routes [...slug] used properly

**Fail Condition**: Incorrect dynamic route setup

### VR-NEXT-010: Image Optimization
**Severity**: Warning
**Check**: Images use next/image

Verify:
- next/image for all images
- Width and height or fill specified
- Alt text present
- No raw img tags

**Fail Condition**: Unoptimized images

### VR-NEXT-011: Link Component
**Severity**: Warning
**Check**: Navigation uses next/link

Verify:
- next/link for internal navigation
- No raw anchor tags for internal
- Prefetch configured appropriately

**Fail Condition**: Raw anchor for internal links

### VR-NEXT-012: Parallel Routes
**Severity**: Info
**Check**: Parallel routes used correctly

Verify:
- @folder naming convention
- default.tsx provided
- Proper slot usage in layout

**Fail Condition**: Incomplete parallel route setup

## Caching Validation

### VR-CACHE-001: Fetch Cache
**Severity**: Info
**Check**: fetch calls have cache config

Options:
- `cache: 'force-cache'` (default)
- `cache: 'no-store'`
- `next: { revalidate: seconds }`

### VR-CACHE-002: Route Segment Config
**Severity**: Info
**Check**: Route segments export config

Verify:
- `export const dynamic`
- `export const revalidate`
- Consistent with data needs

## Output Format

```json
{
  "validator": "nextjs",
  "status": "APPROVED" | "APPROVED_WITH_WARNINGS" | "REJECTED",
  "filesChecked": ["app/page.tsx", "app/layout.tsx"],
  "findings": [
    {
      "rule": "VR-NEXT-001",
      "severity": "warning",
      "file": "app/components/Button.tsx",
      "line": 1,
      "message": "'use client' without client features",
      "suggestion": "Remove 'use client' or add client-specific code"
    }
  ],
  "summary": {
    "errors": 0,
    "warnings": 1,
    "info": 0
  }
}
```

## Context7 Requirements

```
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: "/vercel/next.js",
  topic: "app-router"
})
```
```

### Step 4: Verify Composition
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen
edison compose validators
grep -c "VR-NEXT" .edison/_generated/validators/specialized/nextjs.md
```

## Verification Checklist
- [ ] Core validator created
- [ ] All VR-NEXT rules included
- [ ] Caching rules included
- [ ] Server/Client component rules clear
- [ ] JSON output format documented
- [ ] Context7 requirements specified

## Success Criteria
A complete Next.js validator exists that enforces App Router best practices and catches common mistakes.

## Related Issues
- Audit ID: Wave 5 validator findings
