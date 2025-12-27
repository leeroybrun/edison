<!-- TaskID: 2104-vcon-004-react-validator -->
<!-- Priority: 2104 -->
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

# VCON-004: Create react.md Validator Constitution

## Summary
Create a complete React validator constitution based on the OLD system's ~588-line react.md validator. This specialized validator checks React component patterns, hooks usage, and accessibility.

## Problem Statement
The OLD system had a comprehensive react.md validator (~588 lines). Current Edison correctly delegates to Context7 but needs a unified validator with explicit rules.

## Dependencies
- None

## Objectives
- [x] Create complete react.md validator
- [x] Include hooks best practices
- [x] Include accessibility checks
- [x] Include performance patterns

## Source Files

### Reference - Old Validator
```
/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/specialized/react.md
```

### Output Location
```
/Users/leeroy/Documents/Development/edison/src/edison/data/validators/specialized/react.md
```

## Precise Instructions

### Step 1: Create Validator

Create `/Users/leeroy/Documents/Development/edison/src/edison/data/validators/specialized/react.md`:

```markdown
---
id: react
type: specialized
model: codex
triggers:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/components/**/*"
blocksOnFail: false
---

# React Validator

**Type**: Specialized Validator
**Triggers**: React component files
**Blocking**: No (advisory)

## Constitution Awareness

**Role Type**: VALIDATOR
**Constitution**: `.edison/_generated/constitutions/VALIDATORS.md`

## Validation Scope

This validator checks React implementations for:
1. Component patterns
2. Hooks best practices
3. Accessibility (WCAG AA)
4. Performance optimization
5. State management
6. Props/TypeScript patterns

## Validation Rules

### Component Patterns

#### VR-REACT-001: Component Naming
**Severity**: Warning
**Check**: Components follow naming conventions

Verify:
- PascalCase for components
- camelCase for hooks (useXxx)
- Descriptive, not generic names

**Fail Condition**: Inconsistent naming

#### VR-REACT-002: Component Organization
**Severity**: Info
**Check**: Component structure is consistent

Recommended order:
1. "use client" directive (if needed)
2. Imports
3. Types/Interfaces
4. Component function
5. Subcomponents (if any)
6. Exports

**Fail Condition**: Inconsistent structure

#### VR-REACT-003: Props Interface
**Severity**: Warning
**Check**: Props have TypeScript interface

Verify:
- Interface defined for props
- Props are typed, not `any`
- Optional props marked with ?
- Default values for optional props

**Fail Condition**: Untyped props

### Hooks Best Practices

#### VR-REACT-004: Rules of Hooks
**Severity**: Error
**Check**: Hooks follow rules

Verify:
- Only called at top level
- Only called from React functions
- No conditional hook calls
- Same order every render

**Fail Condition**: Rules of hooks violation

#### VR-REACT-005: useEffect Dependencies
**Severity**: Error
**Check**: useEffect has correct dependencies

Verify:
- All external values in deps array
- No missing dependencies
- Functions memoized or in deps
- Empty deps only for mount-only

**Fail Condition**: Missing or stale dependencies

#### VR-REACT-006: Custom Hook Extraction
**Severity**: Info
**Check**: Logic extracted to custom hooks

When to extract:
- Logic reused across components
- Complex state logic
- Side effect management

**Fail Condition**: Duplicated hook logic

#### VR-REACT-007: useMemo/useCallback Usage
**Severity**: Info
**Check**: Memoization is appropriate

Use memoization for:
- Expensive computations
- Reference equality in deps
- Child component props

Don't over-memoize:
- Primitive values
- Simple operations
- Components without memo()

**Fail Condition**: Over or under memoization

### Accessibility

#### VR-REACT-008: Semantic HTML
**Severity**: Warning
**Check**: Semantic elements used

Verify:
- button for buttons (not div)
- a for links
- form for forms
- Proper heading hierarchy

**Fail Condition**: Non-semantic clickable elements

#### VR-REACT-009: Alt Text
**Severity**: Error
**Check**: Images have alt text

Verify:
- All img/Image have alt
- Alt is descriptive
- Decorative images have alt=""

**Fail Condition**: Missing or empty alt (non-decorative)

#### VR-REACT-010: Keyboard Navigation
**Severity**: Warning
**Check**: Interactive elements are keyboard accessible

Verify:
- tabIndex appropriate
- Focus visible
- Enter/Space for buttons
- Arrow keys for menus

**Fail Condition**: Mouse-only interactions

#### VR-REACT-011: ARIA Labels
**Severity**: Warning
**Check**: ARIA used correctly

Verify:
- aria-label for icon buttons
- aria-labelledby for complex widgets
- No redundant ARIA
- Live regions for dynamic content

**Fail Condition**: Missing or incorrect ARIA

#### VR-REACT-012: Color Contrast
**Severity**: Warning
**Check**: Text has sufficient contrast

Verify:
- 4.5:1 for normal text
- 3:1 for large text
- Focus indicators visible

**Fail Condition**: Insufficient contrast

### Performance

#### VR-REACT-013: Render Prevention
**Severity**: Info
**Check**: Unnecessary renders prevented

Patterns:
- React.memo for pure components
- Key prop for lists
- State colocation
- Context splitting

**Fail Condition**: Obvious render waste

#### VR-REACT-014: List Keys
**Severity**: Error
**Check**: List items have stable keys

Verify:
- Key on immediate child
- Key is stable (not index)
- Key is unique in list

**Fail Condition**: Missing or unstable keys

#### VR-REACT-015: Bundle Impact
**Severity**: Info
**Check**: Component bundle is reasonable

Watch for:
- Large library imports
- Missing tree-shaking
- Heavy client components

**Fail Condition**: Unexpectedly large component

### State Management

#### VR-REACT-016: State Colocation
**Severity**: Info
**Check**: State is close to usage

Verify:
- State in lowest common ancestor
- No prop drilling (use context)
- Server state vs client state

**Fail Condition**: State too high in tree

#### VR-REACT-017: Controlled Components
**Severity**: Warning
**Check**: Form inputs are controlled or uncontrolled consistently

Verify:
- value + onChange (controlled)
- OR defaultValue (uncontrolled)
- Not mixed

**Fail Condition**: Mixed controlled/uncontrolled

## Output Format

```json
{
  "validator": "react",
  "status": "APPROVED" | "APPROVED_WITH_WARNINGS" | "REJECTED",
  "filesChecked": ["components/Button.tsx"],
  "findings": [
    {
      "rule": "VR-REACT-005",
      "severity": "error",
      "file": "components/Counter.tsx",
      "line": 15,
      "message": "useEffect missing dependency: count",
      "suggestion": "Add count to dependencies array"
    }
  ],
  "summary": {
    "errors": 1,
    "warnings": 0,
    "info": 0
  }
}
```

## Context7 Requirements

```
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: "/facebook/react",
  topic: "hooks"
})
```
```

## Verification Checklist
- [ ] Core validator created
- [ ] Component pattern rules included
- [ ] Hooks rules included (VR-REACT-004 through 007)
- [ ] Accessibility rules included (VR-REACT-008 through 012)
- [ ] Performance rules included
- [ ] JSON output format documented

## Success Criteria
A complete React validator exists that enforces hooks best practices, accessibility standards, and performance patterns.

## Related Issues
- Audit ID: Wave 5 validator findings
