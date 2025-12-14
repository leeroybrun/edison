# Tailwind v4 Syntax (CRITICAL)

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
❌ Wrong (v3):
```
@tailwind base;
@tailwind components;
@tailwind utilities;
```

✅ Correct (v4):
```
@import "tailwindcss";
```

- Avoid legacy `@apply` usage in component files; prefer design tokens, utility classes, or `@layer` definitions instead.
<!-- /section: patterns -->
