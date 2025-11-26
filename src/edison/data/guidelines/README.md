# Edison Core Guidelines

Framework-level, project-agnostic guidance consumed by Edison during workflows and
validations. Project layers extend these via includes and project-specific overlays.

## Structure & Contracts

- **Guidelines** (`.edison/core/guidelines/<role>/*.md`): Condensed, mandatory checklists and rules. Always loaded by agents.
- **Extended Guides** (`.edison/core/guides/extended/*.md`): Deep-dive explanations, examples, and philosophy. Referenced by guidelines.
- **Reference** (`.edison/core/guides/reference/*.md`): Specific reference material (APIs, commands).

Role folders under `.edison/core/guidelines/`:
- `shared/` — Applies to all roles.
- `agents/` — Implementation-focused guidance.
- `validators/` — QA, review, and test quality guidance.
- `orchestrators/` — Session orchestration and workflow control.

For topics that exist in both layers (for example `TDD.md`, `SESSION_WORKFLOW.md`):

- The **guideline** includes, near the top of the file, a canonical cross-link of the form  
  `> **Extended Version**: See [core/guides/extended/X.md](../../guides/extended/X.md) for full details.`
- The **extended guide** includes, near the top of the file, a canonical cross-link of the form  
  `> **Condensed Summary**: See [core/guidelines/X.md](../../guidelines/X.md) for the mandatory checklist.`

These bidirectional links are enforced by tests under `.edison/core/tests/guidelines/` so agents can reliably jump between condensed and extended views.

### Pack Guidelines (Namespacing Convention)

- Packs MAY contribute additional guidelines under `.edison/packs/<pack>/guidelines/*.md`.
- Guideline filenames should be **namespaced by pack** to avoid collisions in the global registry, for example:
  - `framework-routing.md`, `framework-metadata.md`
  - `orm-migrations.md`, `orm-query-optimization.md`
  - `test-framework-component-testing.md`, `test-framework-test-quality.md`
- The guideline composition engine discovers these pack guidelines and composes them alongside core and project-level guidelines into `.edison/_generated/guidelines/*.md`.

## Core orchestration & process (mandatory)

- [Session Workflow](./SESSION_WORKFLOW.md) — Active session playbook and queue isolation.
- [Honest Status](./HONEST_STATUS.md) — Canonical status reporting and failure logging.
- [Validation](./VALIDATION.md) — Fail-closed validation workflow and QA expectations.
- [Quality](./QUALITY.md) — Definition of “done”, hygiene, and review bar.
- [Test-Driven Development](./TDD.md) — Core, stack-agnostic TDD loop rules.
- [Context7](./CONTEXT7.md) — External docs usage and context-budget rules.
- [Git Workflow](./GIT_WORKFLOW.md) — Mandatory Git safety and commit rules.
- [Delegation](./DELEGATION.md) — Task delegation, orchestration, and parallelization.
- [State Machine Guards](./orchestrators/STATE_MACHINE_GUARDS.md) — Canonical task/QA state machines.
- [Ephemeral Summaries Policy](./EPHEMERAL_SUMMARIES_POLICY.md) — Where status and QA live.
- [Refactoring](./shared/REFACTORING.md) — Safe, incremental refactoring practices.

## Engineering practice guidelines

- [Architecture](./shared/architecture.md) — High-level structure and design principles.
- [Configuration](./shared/configuration.md) — Configuration design, defaults, and environments.
- [Dependencies](./shared/dependencies.md) — Dependency selection, pinning, and upgrades.
- [Deployment](./orchestrators/deployment.md) — Release, rollout, and rollback guidance.
- [Documentation](./shared/documentation.md) — Documentation structure and expectations.
- [Code Quality](./validators/code-quality.md) — Maintainability, readability, and hygiene.
- [Coding Standards](./shared/coding-standards.md) — Language-agnostic style and conventions.
- [Error Handling](./agents/error-handling.md) — Fail-closed patterns and error classification.
- [Error Recovery](./agents/error-recovery.md) — Recovery paths and resilience patterns.
- [Concurrent Operations](./agents/concurrent-operations.md) — Concurrency, locking, race avoidance.
- [Data Validation](./agents/data-validation.md) — Input validation and normalization rules.
- [API Design](./agents/api-design.md) — HTTP/API design, boundaries, and contracts.
- [Performance](./shared/performance.md) — Budgets, measurement, and optimization.
- [Security](./shared/security.md) — Security controls aligned with OWASP and compliance.
- [Testing](./validators/testing.md) — Testing strategy and CLI testing policy.
- [Testing Patterns](./validators/testing-patterns.md) — Structure, fixtures, and isolation patterns.
- [Naming Conventions](./shared/naming-conventions.md) — Consistent naming for files and symbols.
- [Review Process](./validators/review-process.md) — Code review expectations and checklists.
