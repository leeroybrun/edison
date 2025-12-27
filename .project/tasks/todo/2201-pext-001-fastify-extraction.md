<!-- TaskID: 2201-pext-001-fastify-extraction -->
<!-- Priority: 2201 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: refactor -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave3 -->
<!-- EstimatedHours: 1.5 -->
<!-- DependsOn: Wave 1 -->

# PEXT-001: Extract Wilson Content from Fastify Pack

## Summary
Extract Wilson-specific content from the Edison fastify pack and move it to Wilson project overlays. The pack should contain only technology-specific but project-agnostic content.

## Problem Statement
The fastify pack was extracted directly from Wilson and contains:
- Wilson architecture references (`apps/api`)
- Wilson-specific paths
- Wilson authentication patterns (Better-Auth)
- Wilson API versioning (`/api/v1/dashboard/`)

This content should be in Wilson overlays, not the generic Edison pack.

## Objectives
- [x] Identify Wilson-specific content in fastify pack
- [x] Create/update Wilson overlay files
- [x] Remove Wilson content from pack
- [x] Verify pack remains functional

## Source Files

### Fastify Pack Location
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/fastify/
```

### Wilson Overlay Destination
```
/Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/
```

## Precise Instructions

### Step 1: Audit Pack Content
```bash
cd /Users/leeroy/Documents/Development/edison/src/edison/packs/fastify
find . -name "*.md" -exec echo "=== {} ===" \; -exec grep -l "wilson\|apps/api\|dashboard\|Better-Auth\|/api/v1" {} \;
```

### Step 2: Identify Wilson-Specific Lines

Search for patterns:
- `apps/api` - Wilson monorepo path
- `/api/v1/dashboard/` - Wilson API prefix
- `Better-Auth` - Wilson auth library
- `dashboard_` - Wilson table prefix
- Specific role names (admin, manager, agent, viewer)

### Step 3: Extract to Wilson Overlays

For each Wilson-specific section found:

1. Create overlay file if not exists:
```bash
mkdir -p /Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/packs/fastify/
```

2. Move Wilson content to overlay:
```markdown
# Wilson Fastify Overlay

## Project-Specific Patterns

### API Structure
- Base path: `/api/v1/dashboard/`
- Workspace: `apps/api`
- Auth: Better-Auth with session validation

### Authentication
- Use `getSessionFromRequest()` from Better-Auth
- Extract user from session for authorization
- Role hierarchy: ADMIN > OPERATOR > VIEWER
```

### Step 4: Generalize Pack Content

Replace Wilson-specific examples with generic ones:

**Before:**
```markdown
## API Route Example
```typescript
// apps/api/src/routes/leads.ts
fastify.get('/api/v1/dashboard/leads', async (req, reply) => {
```

**After:**
```markdown
## API Route Example
```typescript
// src/routes/resource.ts
fastify.get('/api/v1/resource', async (req, reply) => {
```

### Step 5: Verify Pack Functionality
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen
edison compose agents
edison compose validators
# Verify output includes fastify patterns
```

## Content Categories

### Keep in Pack (Technology-Specific)
- Fastify route handler patterns
- Fastify plugin architecture
- Fastify schema validation
- Error handling with Fastify
- Fastify hooks (onRequest, preHandler)

### Move to Wilson Overlay (Project-Specific)
- `apps/api` paths
- `/api/v1/dashboard/` routes
- Better-Auth integration
- Wilson role names
- Wilson response envelope format

## Verification Checklist
- [ ] No `apps/api` in pack files
- [ ] No `/api/v1/dashboard/` in pack files
- [ ] No `Better-Auth` in pack files
- [ ] Wilson overlay exists with extracted content
- [ ] Pack still has valid Fastify examples
- [ ] Composition works for Wilson project

## Success Criteria
Fastify pack contains only technology-specific patterns that would work for ANY Fastify project, not just Wilson.

## Related Issues
- Content Placement Audit: Edison packs 30% contaminated
