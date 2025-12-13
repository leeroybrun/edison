# global overlay for Tailwind pack

<!-- extend: tech-stack -->
## Tailwind CSS Validation Context

### Guidelines
{{include:packs/tailwind/guidelines/tailwind/v4-syntax.md}}
{{include:packs/tailwind/guidelines/tailwind/TAILWIND_V4_RULES.md}}
{{include:packs/tailwind/guidelines/tailwind/design-tokens.md}}
{{include:packs/tailwind/guidelines/tailwind/responsive.md}}

### Concrete Checks
- Use Tailwind v4 import syntax (no `@tailwind base/components/utilities`).
- Apply `font-sans` to text elements by default.
- Prefer utility classes; minimize custom CSS.
- Support light and dark modes.
<!-- /extend -->
