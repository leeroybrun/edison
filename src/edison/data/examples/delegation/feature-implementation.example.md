# Feature Implementation Delegation (feature-implementer)

## When to delegate
- A new capability spans multiple modules or services and needs end-to-end ownership.
- The work requires strict TDD with real integrations (no mocks) and YAML-driven configuration.
- Legacy code must be removed or reshaped to fit current patterns rather than patched.
- You need rapid delivery while preserving coherence with existing Edison architecture.

## Delegation prompt template
```
You are feature-implementer. Build <feature/outcome> in this repo.
Context: <business goal>, constraints: strict TDD, no mocks, delete legacy paths, all config from YAML (<config file/path>), reuse existing utilities/patterns.
Scope: <affected domains/modules>. Acceptance: <clear criteria>.
Deliverables: code + tests + docs + summary. Run full tests you add.
Report: changes made, tests run/results, follow-up risks.
```

## Expected deliverables
- Implemented feature with behavior driven by YAML configuration (no hardcoded values).
- New or updated tests demonstrating RED→GREEN flow and passing locally.
- Documentation or inline notes explaining decisions and configuration keys.
- Removal of obsolete or duplicate logic; new utilities extracted where reuse is possible.
- Brief change summary plus next steps/risks for the orchestrator.

## Verification checklist
- Examples directory path is used consistently and code follows existing Edison patterns.
- Configuration lives in YAML and is loaded through shared config helpers; no magic numbers/strings.
- Tests cover success and failure paths without mocks; evidence of passing run is provided.
- No legacy fallbacks remain; dead code removed; DRY and SOLID principles preserved.
- Docs/config references updated; lints/static checks (if any) are green.
