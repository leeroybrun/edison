# global overlay for Tailwind pack

<!-- extend: tech-stack -->
## Tailwind CSS Validation Context

### Guidelines
{{include-section:packs/tailwind/guidelines/includes/tailwind/v4-syntax.md#patterns}}
{{include-section:packs/tailwind/guidelines/includes/tailwind/TAILWIND_V4_RULES.md#patterns}}
{{include-section:packs/tailwind/guidelines/includes/tailwind/design-tokens.md#patterns}}
{{include-section:packs/tailwind/guidelines/includes/tailwind/responsive.md#patterns}}

### Concrete Checks
- Use Tailwind v4 import syntax (no `@tailwind base/components/utilities`).
- Apply `font-sans` to text elements by default.
- Prefer utility classes; minimize custom CSS.
- Support light and dark modes.
<!-- /extend -->
