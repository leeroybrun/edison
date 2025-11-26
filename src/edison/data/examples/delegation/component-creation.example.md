# UI Component Delegation (component-builder)

## When to delegate
- A reusable UI component or composable needs to be created or redesigned.
- Behavior/visuals must be driven by YAML/theming tokens rather than inline constants.
- The component should align with existing design system patterns and remove legacy variants.
- You need accessibility, responsiveness, and test coverage added quickly.

## Delegation prompt template
```
You are component-builder. Create/refine <component> for <surface>.
Context: <user story, design link/spec>. Constraints: strict TDD, no mocks, YAML/theming config (<config path>), reuse shared primitives/hooks, remove legacy components.
Acceptance: <states, a11y rules, breakpoints, interactions>.
Deliverables: component + stories/docs + tests + styling tokens. Run new tests.
Report: changes, tests run/results, open questions/risks.
```

## Expected deliverables
- Component implemented with props/state aligned to design and existing primitives.
- Styling driven by tokens/theme/YAML config; no hardcoded colors/sizes.
- Accessibility handled (ARIA, keyboard, focus management) and responsive behavior covered.
- Tests for rendering, states, and interactions using real components (no mocks).
- Storybook/docs or MDX notes showing usage, variants, and configuration keys.

## Verification checklist
- Uses shared design system utilities; no duplicate helper logic.
- Theming/config pulled from YAML or token sources; defaults centralized.
- A11y checks: labels, roles, keyboard flows, focus outlines covered in tests.
- Component API documented; stories/examples run; snapshots (if used) updated intentionally.
- Legacy/duplicate components removed; bundle impact considered.
