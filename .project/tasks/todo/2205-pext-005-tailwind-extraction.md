<!-- TaskID: 2205-pext-005-tailwind-extraction -->
<!-- Priority: 2205 -->
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
<!-- EstimatedHours: 0.5 -->
<!-- DependsOn: Wave 1 -->

# PEXT-005: Extract Wilson Content from Tailwind Pack

## Summary
Extract Wilson-specific content from the Edison tailwind pack.

## Problem Statement
The tailwind pack may contain Wilson color tokens or design-system-specific patterns.

## Objectives
- [x] Audit for Wilson content
- [x] Move project-specific to overlays
- [x] Keep generic Tailwind v4 patterns

## Source Files

### Pack Location
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/tailwind/
```

## Precise Instructions

### Step 1: Audit Pack
```bash
cd /Users/leeroy/Documents/Development/edison/src/edison/packs/tailwind
grep -rn "wilson\|dashboard\|--color-primary" . --include="*.md"
```

### Step 2: Content Categories

**Keep in Pack:**
- Tailwind v4 syntax
- @apply patterns
- Responsive design
- Dark mode patterns
- Design token concepts

**Move to Wilson Overlay:**
- Wilson-specific color values
- Wilson design system tokens

### Step 3: Create Wilson Overlay (if needed)
```markdown
# Wilson Tailwind Overlay

## Design Tokens
- Primary: hsl(var(--primary))
- Background: hsl(var(--background))
- See apps/dashboard/app/globals.css
```

## Verification Checklist
- [ ] Audit complete
- [ ] Wilson colors moved if present
- [ ] Pack contains generic Tailwind patterns

## Success Criteria
Tailwind pack is project-agnostic.
