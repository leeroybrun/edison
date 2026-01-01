# OpenSpec Integration

Importing OpenSpec change proposals into Edison tasks.

Edison integrates with [OpenSpec](https://github.com/Fission-AI/OpenSpec), a spec-driven workflow that organizes work under `openspec/` (notably `openspec/changes/<change-id>/`).

Edison imports OpenSpec changes as **thin reference tasks**: each Edison task links to the OpenSpec change folder and its key files, rather than embedding spec content.

## How OpenSpec Organizes Work

Typical structure:

```
openspec/
  AGENTS.md
  project.md
  changes/
    <change-id>/
      proposal.md
      tasks.md
      specs/
    archive/
      YYYY-MM-DD-<change-id>/
```

OpenSpec also manages root-level assistant instruction stubs (e.g. `AGENTS.md`, `CLAUDE.md`) via marker-delimited blocks so tools can refresh the managed section without overwriting your entire file.

## `edison import openspec`

```bash
edison import openspec <source> [options]
```

`source` can be:
- repo root (contains `openspec/`)
- `openspec/`
- `openspec/changes/`

### Options

- `--prefix`: Task ID prefix (default: `openspec`)
- `--include-archived`: Include `openspec/changes/archive/*`
- `--dry-run`: Preview changes without writing files
- `--no-qa`: Skip creating QA records
- `--json`: Machine-readable output
- `--repo-root`: Override repository root path

## Sync Model

Edison creates **one task per change-id**:

- Edison task id: `{prefix}-{change-id}`
- Title: extracted from the first `# ` heading in `proposal.md` (fallback: `change-id`)
- Description: links to the change folder plus `proposal.md`, `tasks.md` (if present), and `specs/` (if present)
- Tags: `openspec`, `{prefix}`, `openspec-change`

## Workflow Embedded in Imported Tasks

Imported OpenSpec tasks include a workflow section aligned with OpenSpec’s “apply” stage:
- Confirm the proposal is approved before implementation
- Read `proposal.md`, `design.md` (if present), `tasks.md`, and `specs/` deltas
- Implement `tasks.md` sequentially and only mark items complete once done
- Run `openspec validate <change-id> --strict` to confirm formatting/structure
- Edison can optionally auto-sync `tasks.md` checkboxes when the task is marked `validated`

On re-sync:

- Tasks are updated **only when in `todo`** (to preserve in-progress work).
- Tasks missing from OpenSpec are flagged with `removed-from-openspec`.
