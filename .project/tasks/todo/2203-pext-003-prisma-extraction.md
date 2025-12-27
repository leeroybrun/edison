<!-- TaskID: 2203-pext-003-prisma-extraction -->
<!-- Priority: 2203 -->
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
<!-- EstimatedHours: 1 -->
<!-- DependsOn: Wave 1 -->

# PEXT-003: Extract Wilson Content from Prisma Pack

## Summary
Extract Wilson-specific content from the Edison prisma pack and move it to Wilson project overlays.

## Problem Statement
The prisma pack contains Wilson-specific content:
- `dashboard_` table prefix
- Lead/Source model examples
- Wilson schema path (`apps/dashboard/prisma/schema.prisma`)

## Objectives
- [x] Identify Wilson-specific content
- [x] Move to Wilson overlays
- [x] Generalize pack examples

## Source Files

### Pack Location
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/prisma/
```

### Wilson Overlay Destination
```
/Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/packs/prisma/
```

## Precise Instructions

### Step 1: Audit Pack
```bash
cd /Users/leeroy/Documents/Development/edison/src/edison/packs/prisma
grep -rn "dashboard_\|Lead\|Source\|apps/dashboard\|wilson" . --include="*.md"
```

### Step 2: Content to Extract

**Wilson-Specific (move to overlay):**
- `dashboard_` table prefix
- Lead, Source, LeadStatus models
- `apps/dashboard/prisma/schema.prisma` path
- Wilson-specific relationships

**Keep in Pack (generic Prisma):**
- Schema design patterns
- Migration best practices
- Query optimization
- Relationship patterns
- Index guidelines

### Step 3: Create Wilson Overlay
```markdown
# Wilson Prisma Overlay

## Table Naming
- Prefix: `dashboard_`
- Convention: `dashboard_leads`, `dashboard_sources`

## Core Models
- Lead (main entity)
- Source (lead sources)
- LeadStatus (enum-like)

## Schema Location
- `apps/dashboard/prisma/schema.prisma`
```

### Step 4: Generalize Pack
Replace Wilson examples with generic:
- `dashboard_leads` → `users`
- `Lead` model → `User` model
- `apps/dashboard/prisma/` → `prisma/`

## Verification Checklist
- [ ] No `dashboard_` prefix in pack
- [ ] No Wilson models (Lead, Source) in pack
- [ ] Wilson overlay created with specific patterns
- [ ] Pack has valid generic examples

## Success Criteria
Prisma pack works for any Prisma project, using generic User/Post examples instead of Wilson's Lead/Source.
