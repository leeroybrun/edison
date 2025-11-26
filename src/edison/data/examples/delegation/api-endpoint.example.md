# API Endpoint Delegation (api-builder)

## When to delegate
- A new REST/GraphQL/JSON-RPC endpoint is required or an existing one must be refactored.
- Work touches routing, validation, persistence, and needs consistent error semantics.
- Configuration (rate limits, auth modes, upstream URLs) must be YAML-driven, not hardcoded.
- You need schema-first alignment and backwards-incompatible cleanup (no legacy shims).

## Delegation prompt template
```
You are api-builder. Deliver <endpoint name>/<verb>.
Context: <domain + consumer>, constraints: strict TDD, no mocks, delete legacy handlers, config via YAML (<config path>), reuse existing middleware/serializers.
Inputs/outputs: <request/response shapes>. Auth/rate rules: <details>.
Acceptance: <status codes, validation rules, side effects>.
Deliverables: handler + routing + validation + persistence + tests + docs. Run new tests.
Report: changes, tests run/results, follow-ups.
```

## Expected deliverables
- Endpoint handler wired into router with validation, authorization, and error mapping.
- YAML configuration keys for tunables (paths, timeouts, limits, feature flags) with docs.
- Tests covering happy path, validation failures, and edge conditions using real components.
- Updated API documentation (schema/comments/examples) reflecting new contract.
- Removal of obsolete routes or legacy glue; shared utilities extracted instead of duplication.

## Verification checklist
- Router, schemas, and config follow existing Edison patterns; no ad-hoc wiring.
- Responses and errors match documented contract; status codes and bodies asserted in tests.
- Configuration loaded from YAML; defaults centralized; no magic literals in code.
- Tests run and pass; no mocks; integration paths exercised.
- Legacy handlers/routes removed; documentation and changelog updated if applicable.
