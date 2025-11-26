# global overlay for Tailwind pack

<!-- EXTEND: TechStack -->
## Tailwind CSS Validation Context

### Guidelines
{{include:.edison/packs/tailwind/guidelines/v4-syntax.md}}
{{include:.edison/packs/tailwind/guidelines/TAILWIND_V4_RULES.md}}
{{include:.edison/packs/tailwind/guidelines/design-tokens.md}}
{{include:.edison/packs/tailwind/guidelines/responsive.md}}

### Concrete Checks
- Use Tailwind v4 import syntax (no `@tailwind base/components/utilities`).
- Apply `font-sans` to text elements by default.
- Prefer utility classes; minimize custom CSS.
- Support light and dark modes.
<!-- /EXTEND -->
