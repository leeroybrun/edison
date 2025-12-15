# Edison Core Guidelines

Framework-level, project-agnostic guidance consumed by Edison during workflows and
validations. Project layers extend these via includes and project-specific overlays.

## Structure & Contracts

- **Guidelines** (`.edison/_generated/guidelines/<role>/*.md`): Condensed, mandatory checklists and rules. Always loaded by agents.
- **Extended Guides** (`.edison/_generated/guidelines/extended/*.md`): Deep-dive explanations, examples, and philosophy. Referenced by guidelines.
- **Reference** (`.edison/_generated/guidelines/reference/*.md`): Specific reference material (APIs, commands).

Role folders under `.edison/_generated/guidelines/`:
- `shared/` — Applies to all roles.
- `agents/` — Implementation-focused guidance.
- `validators/` — QA, review, and test quality guidance.
- `orchestrators/` — Session orchestration and workflow control.

For topics that exist in both layers (for example `TDD.md`, `SESSION_WORKFLOW.md`):

- The **guideline** includes, near the top of the file, a canonical cross-link of the form  
- The **extended guide** includes, near the top of the file, a canonical cross-link of the form  
  `> **Condensed Summary**: See [core/guidelines/X.md](../../guidelines/X.md) for the mandatory checklist.`

These bidirectional links are enforced by tests under `tests/guidelines/` so agents can reliably jump between condensed and extended views.

### Pack Guidelines (Namespacing Convention)

- Packs MAY contribute additional guidelines under `.edison/_generated/guidelines/<pack>/*.md`.
- Guideline filenames should be **namespaced by pack** to avoid collisions in the global registry, for example:
  - `framework-routing.md`, `framework-metadata.md`
  - `orm-migrations.md`, `orm-query-optimization.md`
  - `test-framework-component-testing.md`, `test-framework-test-quality.md`
- The guideline composition engine discovers these pack guidelines and composes them alongside core and project-level guidelines into `{{PROJECT_EDISON_DIR}}/_generated/guidelines/*.md`.

## Core orchestration & process (mandatory)

- Orchestrator playbook: `orchestrators/SESSION_WORKFLOW.md`
- Orchestrator delegation rules: `orchestrators/DELEGATION.md`
- State machine guards: `orchestrators/STATE_MACHINE_GUARDS.md`
- Shared validation workflow: `shared/VALIDATION.md`
- Shared status reporting: `shared/HONEST_STATUS.md`
- Shared ephemeral summaries policy: `shared/EPHEMERAL_SUMMARIES_POLICY.md`
- Shared git workflow: `shared/GIT_WORKFLOW.md`

## Include-Only Building Blocks

These are designed to be embedded into agent/validator constitutions via `{{include-section:...}}`:

- TDD: `includes/TDD.md`
- No-mocks philosophy: `includes/NO_MOCKS.md`
- Test isolation: `includes/TEST_ISOLATION.md`
- Type safety: `includes/TYPE_SAFETY.md`
- Error handling: `includes/ERROR_HANDLING.md`
- Configuration-first: `includes/CONFIGURATION.md`
- Shared Context7 core blocks: `includes/CONTEXT7.md`

## Role-Specific Guides

- Agents:
  - Mandatory workflow: `agents/MANDATORY_WORKFLOW.md`
  - Output format: `agents/OUTPUT_FORMAT.md`
  - Delegation awareness: `agents/DELEGATION_AWARENESS.md`
- Validators:
  - Validator workflow: `validators/VALIDATOR_WORKFLOW.md`
  - Output format: `validators/OUTPUT_FORMAT.md`
  - Common validator guidance: `validators/VALIDATOR_COMMON.md`
