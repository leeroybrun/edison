<!-- TaskID: 2302-worg-002-tailwind-to-pack -->
<!-- Priority: 2302 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: refactor -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave4 -->
<!-- EstimatedHours: 2 -->
<!-- DependsOn: Wave 3 -->

# WORG-002: Move Tailwind v4 Syntax to Tailwind Pack

## Summary
Move technology-generic Tailwind v4 patterns from Wilson overlays to the Edison tailwind pack.

## Problem Statement
Wilson overlays contain Tailwind v4 patterns that are NOT Wilson-specific:
- @theme directive syntax
- CSS variable approach
- Color function changes
- v3 → v4 migration patterns

These should be in the tailwind pack for all projects.

## Objectives
- [x] Identify Tailwind v4 content in Wilson overlays
- [x] Move to Edison tailwind pack
- [x] Keep Wilson design tokens in overlays

## Source Files

### Wilson Overlays
```
/Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/
```

### Tailwind Pack
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/tailwind/guidelines/
```

## Precise Instructions

### Step 1: Audit Wilson Overlays
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays
grep -rn "@theme\|tailwind.*v4\|oklch\|color-mix" . --include="*.md"
```

### Step 2: Content to Move

**Move to Tailwind Pack:**
- @theme directive usage
- oklch() color syntax
- color-mix() function
- CSS custom properties for theming
- v3 → v4 migration checklist
- Dark mode with @media (prefers-color-scheme)

**Keep in Wilson Overlays:**
- Wilson brand colors (specific values)
- Wilson spacing scale
- Wilson typography settings

### Step 3: Update Tailwind Pack

Add/update `edison/src/edison/packs/tailwind/guidelines/v4-syntax.md`:

```markdown
# Tailwind CSS v4 Syntax

## @theme Directive

Tailwind v4 uses @theme for configuration:

```css
@theme {
  --color-primary: oklch(0.6 0.15 250);
  --spacing-lg: 2rem;
}
```

## Color Functions

### oklch() - Preferred
```css
--color-accent: oklch(0.7 0.2 200);
```
Benefits: Perceptually uniform, better for accessibility

### color-mix()
```css
--color-hover: color-mix(in oklch, var(--primary), black 10%);
```

## Dark Mode

### Automatic (system preference)
```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-background: oklch(0.15 0 0);
  }
}
```

### Class-based
```css
.dark {
  --color-background: oklch(0.15 0 0);
}
```

## Migration from v3

### Breaking Changes
1. @apply requires @theme variables
2. No more theme() function in CSS
3. Colors use CSS variables

### Migration Checklist
- [ ] Convert tailwind.config.js to @theme
- [ ] Replace theme() with var()
- [ ] Update color syntax to oklch
- [ ] Test dark mode
```

### Step 4: Update Wilson Overlays

Keep only Wilson-specific:
```markdown
# Wilson Tailwind Overlay

## Brand Colors
- Primary: oklch(0.6 0.15 250) /* Wilson blue */
- Accent: oklch(0.7 0.2 180) /* Wilson teal */

## Design Tokens
See apps/dashboard/app/globals.css for full token list.
```

## Verification Checklist
- [ ] Tailwind v4 syntax in pack
- [ ] Wilson overlays only have brand colors
- [ ] Other projects can use v4 patterns

## Success Criteria
Any project using tailwind pack gets v4 patterns.
