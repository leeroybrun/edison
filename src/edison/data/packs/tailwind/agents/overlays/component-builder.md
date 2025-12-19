# component-builder overlay for Tailwind pack

<!-- extend: tools -->
- Tailwind CSS v4 with `@import "tailwindcss"` syntax; config in `postcss.config.mjs` using `@tailwindcss/postcss` plugin.
- Dark theme design tokens from your project's design guidelines.
- Run your project's lint/test commands to verify UI quality (avoid hardcoded workspace filters).
<!-- /extend -->

<!-- extend: guidelines -->
- Use v4 syntax (no `@tailwind base/components/utilities`); clear `.next` cache if utilities fail.
- Always add `font-sans` and dark-theme colors; prefer arbitrary values for custom palette.
- Build accessible, responsive components; keep class names concise with `cn` helper.
- Follow Context7 for React 19/Next 16/Tailwind v4 updates before coding.
<!-- /extend -->

<!-- section: TailwindV4Patterns -->
## CRITICAL: Tailwind CSS v4 Syntax

**Tailwind v4 is DIFFERENT from v3!** Using v3 syntax will break styling.

### Rule 1: CSS Import (NOT `@tailwind` directives)

```css
/* globals.css - CORRECT v4 syntax */
@import "tailwindcss";

/* WRONG - v3 syntax does NOT work in v4! */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### Rule 2: Always add `font-sans` to text elements

```tsx
// CORRECT - explicit font-sans
<h1 className="text-3xl font-bold font-sans">Title</h1>
<p className="text-base font-sans">Body text</p>

// WRONG - may render as Times New Roman
<h1 className="text-3xl font-bold">Title</h1>
```

### Rule 3: Use arbitrary values for custom colors

```tsx
// CORRECT - arbitrary values for custom palette
<div className="bg-[#0a0a0a] text-[#e8e8e8] border-[#222222]">

// WRONG - hardcoded Tailwind colors (may not match design)
<div className="bg-gray-900 text-white border-gray-700">
```

### Rule 4: Clear `.next` cache after CSS changes

```bash
# If styles don't apply, clear cache and restart
  rm -rf <framework-cache-dir> && {{function:ci_command("dev")}}
```

### Rule 5: PostCSS plugin (v4 syntax)

```javascript
// postcss.config.mjs - CORRECT v4
export default {
  plugins: {
    '@tailwindcss/postcss': {},  // v4 plugin
  },
}

// WRONG - v3 plugin
export default {
  plugins: {
    tailwindcss: {},  // v3 plugin - won't work
  },
}
```

## Red Flags (indicates v3 syntax was used)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Times New Roman font | Missing `font-sans` | Add `font-sans` to text elements |
| No spacing/borders | Utilities not applying | Clear `.next` cache |
| White backgrounds in dark theme | Wrong color values | Use arbitrary values `bg-[#hex]` |
| Styles not updating | PostCSS caching | Delete `.next`, restart dev server |

## v3 to v4 Migration Quick Reference

| v3 Syntax | v4 Syntax |
|-----------|-----------|
| `@tailwind base` | `@import "tailwindcss"` |
| `tailwindcss` plugin | `@tailwindcss/postcss` plugin |
| `tailwind.config.js` theme | `@theme` in CSS |
| `bg-gray-900` | `bg-[#111]` or CSS variable |

## Component Example

```tsx
import { type ComponentProps } from 'react'
import { cn } from '<utils-module>'

interface MetricCardProps extends ComponentProps<'div'> {
  title: string
  value: string | number
  trend?: { value: number; direction: 'up' | 'down' }
  icon?: React.ReactNode
}

export function MetricCard({
  title,
  value,
  trend,
  icon,
  className,
  ...props
}: MetricCardProps) {
  return (
    <div
      className={cn(
        'bg-[#111111] border border-[#222222] rounded-lg p-6',
        className
      )}
      {...props}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-[#999999] font-sans">
          {title}
        </h3>
        {icon && <div className="text-[#666666]">{icon}</div>}
      </div>

      <div className="flex items-end justify-between">
        <p className="text-3xl font-bold text-[#e8e8e8] font-sans">
          {value}
        </p>

        {trend && (
          <div
            className={cn(
              'text-sm font-medium font-sans',
              trend.direction === 'up' ? 'text-green-500' : 'text-red-500'
            )}
          >
            {trend.direction === 'up' ? '↑' : '↓'} {Math.abs(trend.value)}%
          </div>
        )}
      </div>
    </div>
  )
}
```
<!-- /section: TailwindV4Patterns -->




