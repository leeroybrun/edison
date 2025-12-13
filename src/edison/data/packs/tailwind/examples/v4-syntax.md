# Tailwind CSS v4 – Theme Syntax Example

This example shows how this example project uses **Tailwind CSS 4** with the
CSS‑first `@theme` directive to map design tokens to utility classes.

```css
/* app/globals.css (or your project's global stylesheet) */

@import "tailwindcss";

@theme {
  /* Project brand + surface tokens expressed as OKLCH */
  --color-primary: oklch(29.2% 0.31 264.8);
  --color-surface: oklch(12% 0.02 260);
  --color-border: oklch(20% 0.03 260);

  /* Typography */
  --font-sans: "Inter", system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
}

:root {
  /* Map tokens used by components into @theme variables */
  --primary: 29.2% 0.31 264.8;
  --surface: 12% 0.02 260;
  --border: 20% 0.03 260;
}

.dark {
  /* Dark-mode adjustments can tweak OKLCH values while keeping the same hue */
  --surface: 10% 0.02 260;
  --border: 18% 0.03 260;
}
```

Usage in components:

```tsx
// Premium button using Tailwind v4 classes wired to @theme tokens
export function PrimaryButton(props: React.ComponentProps<'button'>) {
  return (
    <button
      {...props}
      className="bg-primary text-primary-foreground border-border rounded-md px-4 py-2 font-sans"
    />
  );
}
```

Key rules:

- Define colors and tokens in `@theme`, not in components.
- Avoid hard‑coded hex values like `bg-[#222222]`; use semantic classes instead.
- When adjusting palette, update `globals.css` and `@theme` once—components stay unchanged.
