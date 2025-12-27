<!-- TaskID: 2204-pext-004-react-extraction -->
<!-- Priority: 2204 -->
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

# PEXT-004: Extract Wilson Content from React Pack

## Summary
Extract Wilson-specific content from the Edison react pack and move it to Wilson project overlays.

## Problem Statement
The react pack may contain Wilson-specific content:
- Wilson component examples
- shadcn/ui specific patterns (if too Wilson-focused)
- Dashboard UI patterns

## Objectives
- [x] Audit for Wilson content
- [x] Move project-specific to overlays
- [x] Keep generic React patterns

## Source Files

### Pack Location
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/react/
```

### Wilson Overlay Destination
```
/Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/packs/react/
```

## Precise Instructions

### Step 1: Audit Pack
```bash
cd /Users/leeroy/Documents/Development/edison/src/edison/packs/react
grep -rn "wilson\|dashboard\|Lead\|@/components" . --include="*.md"
```

### Step 2: Content Categories

**Wilson-Specific (if found):**
- Wilson component names
- Wilson-specific hooks
- Dashboard layout patterns

**Keep in Pack (generic React):**
- React 19 features
- Hooks best practices
- Component patterns
- Accessibility guidelines
- Performance optimization

### Step 3: Create Wilson Overlay (if needed)
```markdown
# Wilson React Overlay

## Component Library
- Use shadcn/ui components
- Import from `@/components/ui`

## Design System
- Follow Wilson DESIGN.md
- Use Tailwind design tokens
```

## Verification Checklist
- [ ] Audit complete
- [ ] Wilson content moved (if any found)
- [ ] Pack contains generic React patterns only

## Success Criteria
React pack is project-agnostic and works for any React project.
