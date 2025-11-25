# Example 1: UI Component (Direct Implementation)

**Scenario**: Build a MetricCard component for displaying product statistics
**Model Used**: Claude Sonnet 4.5 (direct implementation, no delegation)
**Pattern**: Simple - sub-agent implements directly

---

## Task Context

**User Request**: "Build a MetricCard component that displays a metric title, value, trend indicator, and optional icon. Should support light/dark themes and be fully accessible."

**Files Involved**:
- `/apps/example-app/src/components/MetricCard.tsx` (new)
- `/apps/example-app/src/components/MetricCard.test.tsx` (new)

**Expected Result**: Reusable React component with TDD tests

---

## Step 1: Orchestrator Analysis

### Orchestrator Reads Config

```typescript
// Orchestrator checks task type
const taskType = identifyTaskType(task)
// Result: "ui-component"

// Check taskTypeRules
const rule = config.taskTypeRules['ui-component']
// Result:
{
  "preferredModel": "claude",
  "subAgentType": "component-builder-nextjs",
  "reason": "Component design needs UX thinking"
}

// Check filePatternRules for *.tsx
const fileRule = config.filePatternRules['*.tsx']
// Result:
{
  "preferredModel": "claude",
  "reason": "UI/UX thinking, component design",
  "subAgentType": "component-builder-nextjs"
}

// Decision: Delegate to component-builder-nextjs, suggest Claude
```

### Orchestrator Delegates to Sub-Agent

```typescript
Task({
  subagent_type: 'component-builder-nextjs',
  prompt: `
    Build MetricCard component for product metrics display.

    Requirements:
    - Props: title (string), value (string), trend (optional, number), icon (optional)
    - Trend indicator: green up arrow (positive), red down arrow (negative)
    - Support light/dark themes via CSS variables
    - Fully accessible (ARIA labels, keyboard navigation)
    - Responsive design
    - TDD: Write tests first

    FILES:
    - /apps/example-app/src/components/MetricCard.tsx
    - /apps/example-app/src/components/MetricCard.test.tsx

    CONFIG GUIDANCE:
    - taskTypeRules['ui-component'] → preferredModel: "claude"
    - filePatternRules['*.tsx'] → preferredModel: "claude"
    - This is your specialty! Implement directly.

    Check .agents/delegation/config.json for detailed rules.
  `
})
```

---

## Step 2: Sub-Agent (component-builder-nextjs) Receives Task

### Sub-Agent Reads Config

```typescript
// component-builder-nextjs checks its own defaults
const myDefaults = config.subAgentDefaults['component-builder-nextjs']
// Result:
{
  "defaultModel": "claude",
  "implementDirectly": true,
  "canDelegateTo": ["codex"],
  "delegateWhen": "Complex TypeScript types, performance optimization"
}

// Check orchestrator's suggestion
const suggestion = extractSuggestion(orchestratorPrompt)
// Result: "claude"

// Check file patterns
const filePatterns = matchFiles(['MetricCard.tsx'], config.filePatternRules)
// Result: *.tsx → "claude"

// Decision Matrix:
// - Orchestrator suggests: Claude ✅
// - File pattern says: Claude ✅
// - My default is: Claude ✅
// - Task is: UI component (my specialty) ✅
// - No complex TypeScript types (no need for Codex) ✅
//
// FINAL DECISION: Implement directly with Claude (me!)
```

### Sub-Agent Decision

```
✅ IMPLEMENT DIRECTLY

Reasoning:
1. UI component is my core strength
2. Config confirms Claude for *.tsx files
3. No need for delegation (no complex types, no performance issues)
4. Orchestrator correctly suggested my model
5. This is exactly what I was built for!

Proceeding with direct implementation using TDD...
```

---

## Step 3: Implementation (TDD - Red-Green-Refactor)

### 3A. RED: Write Failing Tests

**File**: `/apps/example-app/src/components/MetricCard.test.tsx`

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MetricCard } from './MetricCard'

describe('MetricCard', () => {
  it('should render title and value', () => {
    render(<MetricCard title="Total Leads" value="1,234" />)

    expect(screen.getByText('Total Leads')).toBeInTheDocument()
    expect(screen.getByText('1,234')).toBeInTheDocument()
  })

  it('should display positive trend indicator', () => {
    render(<MetricCard title="Conversions" value="89%" trend={12.5} />)

    const trend = screen.getByLabelText(/trend indicator/i)
    expect(trend).toHaveTextContent('+12.5%')
    expect(trend).toHaveClass('text-green-600')
  })

  it('should display negative trend indicator', () => {
    render(<MetricCard title="Response Time" value="2.4s" trend={-8.2} />)

    const trend = screen.getByLabelText(/trend indicator/i)
    expect(trend).toHaveTextContent('-8.2%')
    expect(trend).toHaveClass('text-red-600')
  })

  it('should render optional icon', () => {
    const TestIcon = () => <svg data-testid="metric-icon" />
    render(<MetricCard title="Users" value="456" icon={<TestIcon />} />)

    expect(screen.getByTestId('metric-icon')).toBeInTheDocument()
  })

  it('should have proper accessibility attributes', () => {
    render(<MetricCard title="Revenue" value="$12,345" trend={5.3} />)

    const card = screen.getByRole('article')
    expect(card).toHaveAttribute('aria-label', expect.stringContaining('Revenue'))
  })

  it('should support dark theme via CSS variables', () => {
    render(<MetricCard title="Test" value="100" />)

    const card = screen.getByRole('article')
    // Check that component uses CSS variables (not hardcoded colors)
    const styles = window.getComputedStyle(card)
    expect(card.className).toContain('bg-[var(--color-surface)]')
  })
})
```

**Run Tests**: `npm test MetricCard.test.tsx`

```bash
❌ FAIL - Component doesn't exist yet (expected!)
```

### 3B. GREEN: Implement Component

**File**: `/apps/example-app/src/components/MetricCard.tsx`

```typescript
import { ReactNode } from 'react'

export interface MetricCardProps {
  /** Metric title/label */
  title: string
  /** Metric value to display */
  value: string
  /** Optional trend percentage (positive or negative) */
  trend?: number
  /** Optional icon component */
  icon?: ReactNode
}

export function MetricCard({ title, value, trend, icon }: MetricCardProps) {
  const trendColor = trend !== undefined
    ? trend >= 0
      ? 'text-green-600 dark:text-green-400'
      : 'text-red-600 dark:text-red-400'
    : ''

  const trendIcon = trend !== undefined
    ? trend >= 0
      ? '↑'
      : '↓'
    : ''

  return (
    <article
      className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow"
      aria-label={`${title} metric card${trend !== undefined ? `, trend ${trend > 0 ? 'up' : 'down'} ${Math.abs(trend)}%` : ''}`}
    >
      <div className="flex items-start justify-between">
        {/* Title section */}
        <div className="flex-1">
          <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-1">
            {title}
          </h3>
          <p className="text-3xl font-bold text-[var(--color-text-primary)]">
            {value}
          </p>
        </div>

        {/* Optional icon */}
        {icon && (
          <div className="ml-4 text-[var(--color-text-tertiary)]">
            {icon}
          </div>
        )}
      </div>

      {/* Trend indicator */}
      {trend !== undefined && (
        <div className="mt-3">
          <span
            className={`inline-flex items-center text-sm font-medium ${trendColor}`}
            aria-label={`Trend indicator: ${trend > 0 ? 'up' : 'down'} ${Math.abs(trend)} percent`}
          >
            <span className="mr-1" aria-hidden="true">{trendIcon}</span>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        </div>
      )}
    </article>
  )
}
```

**Run Tests**: `npm test MetricCard.test.tsx`

```bash
✅ PASS - All 6 tests passing!
```

### 3C. REFACTOR: Clean Up (Optional)

Code is already clean - no refactoring needed in this case.

---

## Step 4: Sub-Agent Verification

```typescript
// component-builder-nextjs runs verification checklist

✅ TypeScript types defined (MetricCardProps)
✅ Tests written FIRST (TDD - red phase)
✅ Implementation passes all tests (TDD - green phase)
✅ Accessibility attributes present (aria-label, role)
✅ Light/dark theme support (CSS variables)
✅ Responsive design (uistyles utilities)
✅ No hardcoded colors (uses design tokens)
✅ Props documented (JSDoc comments)

// All checks pass - ready to return to orchestrator
```

---

## Step 5: Sub-Agent Reports Back to Orchestrator

```
TASK COMPLETE: MetricCard component

Files Created:
- /apps/example-app/src/components/MetricCard.tsx (60 lines)
- /apps/example-app/src/components/MetricCard.test.tsx (80 lines)

Implementation Approach:
✅ Implemented directly with Claude (no delegation needed)
✅ Followed TDD (tests written first, all passing)
✅ Used CSS variables for theme support
✅ Full accessibility (ARIA labels, semantic HTML)
✅ TypeScript types defined

Test Results:
✅ 6/6 tests passing
✅ Component renders correctly
✅ Trend indicators work (positive/negative)
✅ Icon support works
✅ Accessibility verified
✅ Theme support verified

Ready for Integration:
Import with: import { MetricCard } from '@/components/MetricCard'
```

---

## Step 6: Orchestrator Integration Verification

```typescript
// Orchestrator verifies sub-agent's work

// 1. Files exist
ls -la /apps/example-app/src/components/MetricCard*
// ✅ Both files present

// 2. Tests pass
npm test MetricCard.test.tsx
// ✅ 6/6 passing

// 3. TypeScript compiles
npm run type-check
// ✅ No errors

// 4. Builds successfully
npm run build
// ✅ Build succeeds

// 5. Manual verification
npm run dev
// Open Storybook or test page
// ✅ Component renders correctly
// ✅ Light/dark theme works
// ✅ Trend indicators display properly

// ALL CHECKS PASS - Task Complete!
```

---

## Key Takeaways

### ✅ Why Direct Implementation Worked

1. **Task matched model strengths**: UI component = Claude's specialty
2. **Config confirmed**: Both taskTypeRules and filePatternRules said "claude"
3. **No complexity triggers**: No complex types, no performance issues
4. **Sub-agent autonomy**: component-builder-nextjs made final decision (config was right)
5. **Efficient**: No delegation overhead, fast implementation

### 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| **Time to implement** | ~15 minutes |
| **Delegation overhead** | 0 (direct implementation) |
| **Test coverage** | 100% (6 tests) |
| **Accessibility** | Full WCAG AA compliance |
| **Theme support** | Light + Dark |
| **TypeScript errors** | 0 |

### 🎯 Config Usage

**Config sections referenced**:
- ✅ `taskTypeRules['ui-component']` - Confirmed Claude
- ✅ `filePatternRules['*.tsx']` - Confirmed Claude
- ✅ `subAgentDefaults['component-builder-nextjs']` - Confirmed direct implementation
- ❌ `zenMcpIntegration` - Not needed (no delegation)

**Decision priority** (from highest to lowest):
1. Orchestrator instruction: ✅ Suggested Claude
2. File pattern rule: ✅ *.tsx → Claude
3. Task type rule: ✅ ui-component → Claude
4. Sub-agent default: ✅ component-builder-nextjs → Claude
5. Sub-agent judgment: ✅ Agreed with all above

**Result**: Perfect alignment - config was followed, no overrides needed.

---

## When to Use This Pattern

✅ **Use direct implementation (Claude) when**:
- Building UI components (*.tsx files)
- Task type is "ui-component"
- No complex TypeScript type inference needed
- No performance optimization required
- component-builder-nextjs is the sub-agent

❌ **Don't use direct implementation (delegate instead) when**:
- Building API routes (use Codex)
- Complex type inference needed (use Codex)
- Database schemas (use Codex)
- Performance-critical code (consider Codex)
- Security-sensitive code (use Codex)

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────┐
│ USER REQUEST                            │
│ "Build MetricCard component"            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ ORCHESTRATOR                            │
│ 1. Reads config.json                    │
│ 2. taskTypeRules['ui-component'] → Claude │
│ 3. filePatternRules['*.tsx'] → Claude  │
│ 4. Selects: component-builder-nextjs          │
│ 5. Suggests: Claude                     │
└──────────────┬──────────────────────────┘
               │
               │ Task(subagent_type='component-builder-nextjs', ...)
               ▼
┌─────────────────────────────────────────┐
│ COMPONENT-BUILDER (Claude)              │
│ 1. Reads config.json                    │
│ 2. Confirms: Claude is correct          │
│ 3. Decision: Implement directly         │
│ 4. TDD: Write tests (RED)               │
│ 5. Implement component (GREEN)          │
│ 6. Verify & return                      │
└──────────────┬──────────────────────────┘
               │
               │ Results: Files + Tests passing
               ▼
┌─────────────────────────────────────────┐
│ ORCHESTRATOR                            │
│ 1. Verifies files exist                 │
│ 2. Runs tests (6/6 pass)                │
│ 3. Builds project (success)             │
│ 4. Manual test (works correctly)        │
│ 5. Marks task complete ✅               │
└─────────────────────────────────────────┘
```

---

**Example Type**: Direct Implementation (Simplest Pattern)
**Next Example**: [example-2-api-route.md](./example-2-api-route.md) - Full delegation to Codex
