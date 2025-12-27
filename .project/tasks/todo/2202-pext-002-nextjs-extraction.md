<!-- TaskID: 2202-pext-002-nextjs-extraction -->
<!-- Priority: 2202 -->
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

# PEXT-002: Extract Wilson Content from Next.js Pack

## Summary
Extract Wilson-specific content from the Edison nextjs pack and move it to Wilson project overlays.

## Problem Statement
The nextjs pack contains Wilson-specific content:
- `apps/dashboard` paths
- Wilson component patterns
- Wilson API route patterns (`/api/v1/dashboard/`)

## Objectives
- [x] Identify Wilson-specific content
- [x] Move to Wilson overlays
- [x] Generalize pack examples

## Source Files

### Pack Location
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/nextjs/
```

### Wilson Overlay Destination
```
/Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/packs/nextjs/
```

## Precise Instructions

### Step 1: Audit Pack
```bash
cd /Users/leeroy/Documents/Development/edison/src/edison/packs/nextjs
grep -rn "apps/dashboard\|wilson\|/api/v1/dashboard" . --include="*.md"
```

### Step 2: Content to Extract

**Wilson-Specific (move to overlay):**
- `apps/dashboard` workspace references
- Wilson API path patterns
- Dashboard-specific component examples
- Wilson auth UI patterns

**Keep in Pack (generic Next.js):**
- App Router patterns
- Server/Client component rules
- Layout/Page conventions
- Route handler patterns
- Metadata configuration

### Step 3: Create Wilson Overlay
```bash
mkdir -p /Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/packs/nextjs/
```

Create overlay content:
```markdown
# Wilson Next.js Overlay

## Project Structure
- Dashboard app: `apps/dashboard`
- API routes: `/api/v1/dashboard/*`

## Component Patterns
- Use shadcn/ui components from `@/components/ui`
- Follow Wilson design system
```

### Step 4: Generalize Pack
Replace Wilson paths with generic:
- `apps/dashboard` → `app`
- `/api/v1/dashboard/` → `/api/v1/`

## Verification Checklist
- [ ] No `apps/dashboard` in pack
- [ ] No Wilson-specific patterns in pack
- [ ] Wilson overlay created
- [ ] Pack has valid generic examples

## Success Criteria
Next.js pack works for any Next.js project, not just Wilson.
