# component-builder-tailwind (Tailwind CSS v4)

## Tools
- Tailwind CSS v4 with `@import "tailwindcss"` syntax; config in `postcss.config.mjs` using `@tailwindcss/postcss` plugin.
- Dark theme design tokens from `../DESIGN.md`.
- `pnpm lint --filter dashboard` and `pnpm test --filter dashboard` for UI.

## Guidelines
- Use v4 syntax (no `@tailwind base/components/utilities`); clear `.next` cache if utilities fail.
- Always add `font-sans` and dark-theme colors; prefer arbitrary values for custom palette.
- Build accessible, responsive components; keep class names concise with `cn` helper.
- Follow Context7 for React 19/Next 16/Tailwind v4 updates before coding.
- Example structure:
```tsx
export function MetricCard({ title, value, trend, icon, className, ...props }: MetricCardProps) {
  return (
    <div className={cn('bg-[#111] border border-[#222] rounded-lg p-6', className)} {...props}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-[#999] font-sans">{title}</h3>
        {icon && <div className="text-[#666]">{icon}</div>}
      </div>
      <div className="flex items-end justify-between">
        <p className="text-3xl font-bold text-[#e8e8e8] font-sans">{value}</p>
        {trend && (
          <div className={cn('text-sm font-medium font-sans', trend.direction === 'up' ? 'text-green-500' : 'text-red-500')}>
            {trend.direction === 'up' ? '↑' : '↓'} {Math.abs(trend.value)}%
          </div>
        )}
      </div>
    </div>
  )
}
```
