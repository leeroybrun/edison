# Tailwind v4 Syntax (CRITICAL)

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
