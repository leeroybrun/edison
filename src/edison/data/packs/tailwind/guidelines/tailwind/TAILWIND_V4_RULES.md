# Tailwind CSS v4 Detailed Rules

<!-- SECTION: import-syntax -->
## Rule 1 — Import syntax only

Use the v4 CSS-first import at the top of the global stylesheet:

```css
@import "tailwindcss";
```

Do **not** use v3 directives (`@tailwind base|components|utilities`) because they are ignored by v4.
<!-- /SECTION: import-syntax -->

<!-- SECTION: font-sans -->
## Rule 2 — Apply `font-sans` explicitly

Tailwind v4 no longer injects the default font stack automatically. Add `font-sans` on the root layout and any text elements to avoid Times New Roman fallbacks.
<!-- /SECTION: font-sans -->

<!-- SECTION: arbitrary-values -->
## Rule 3 — Prefer arbitrary values for custom palette

When you need colors outside the design tokens, use arbitrary values (e.g., `bg-[#0a0a0a]`, `text-[#e8e8e8]`). Avoid guessing with the default Tailwind palette when a precise value is required.
<!-- /SECTION: arbitrary-values -->

<!-- SECTION: cache-clear -->
## Rule 4 — Clear build cache after CSS changes

If utilities stop applying, clear the framework cache before debugging:

```bash
rm -rf .next && npm run dev
```

Stale `.next` artifacts are a common source of "class not found" issues in v4.
<!-- /SECTION: cache-clear -->

<!-- SECTION: postcss-v4 -->
## Rule 5 — Use the v4 PostCSS preset

Configure PostCSS with the official v4 preset and avoid the legacy plugin:

```js
// postcss.config.mjs
export default {
  plugins: {
    '@tailwindcss/postcss': {}, // ✅ v4 preset
  },
}
```

The legacy `tailwindcss` plugin will fail to generate utilities in v4.
<!-- /SECTION: postcss-v4 -->

<!-- SECTION: theme-tokens -->
## Rule 6 — Define tokens in `@theme`

Express design tokens as CSS variables inside an `@theme` block so components stay in sync with the theme source of truth:

```css
@theme {
  --color-surface: oklch(18% 0.02 260);
  --color-border: oklch(28% 0.03 260);
  --font-sans: "Inter", system-ui, -apple-system, sans-serif;
}
```

Use the generated classes (`bg-surface`, `border-border`, `font-sans`) instead of hardcoding values in components.
<!-- /SECTION: theme-tokens -->
