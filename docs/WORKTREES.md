# Worktrees + Meta Branch (Shared State)

Edison uses **git worktrees** so you can work in parallel without switching the primary checkout, and it uses a **meta worktree/branch** to keep “project state” (tasks, QA, tool config) shared across all worktrees.

This document describes what is **tracked**, what is **symlinked**, what is **ignored**, and why.

## Terms

- **Primary checkout**: your normal repo folder (e.g. `.../edison-ui`).
- **Session worktree**: a per-session git worktree (e.g. `.../edison-ui-worktrees/<sessionId>`).
- **Meta worktree**: a special git worktree (default path `.../<project>-worktrees/_meta`) checked out on the **meta branch** (default name `edison-meta`).
- **Shared state**: directories/files that should be the same across primary + all session worktrees.

## Why meta mode exists

Git worktrees **do not share untracked files**, so anything “local-first” (tasks, QA, logs) would otherwise appear empty inside a worktree.

Also, if you track those files on code branches, you’ll get merge conflicts and branch divergence. Meta mode avoids that by giving shared state a single canonical home.

## What lives where (default meta setup)

### 1) Local management state (`.project/*`)

- Canonical location: **meta worktree** (`<meta>/.project/…`)
- In primary + session worktrees: `.project/{tasks,qa,logs,archive,sessions}` are **symlinks** pointing into the meta worktree.
- Rationale: task/QA commands work the same everywhere, and state is not tied to code branches.

### 2) Bootstrap configuration (`.edison/config/*`)

- Location: **tracked in code branches** (primary + session worktrees each have a real `.edison/config` directory from the branch checkout).
- Not symlinked by default.
- Rationale: Edison must be able to read config before it knows where/how to link the meta worktree.

If you want config to be shared across all worktrees, do it by editing config in your code branch and letting Git propagate it as normal code/config.

### 3) Composed artifacts (`.edison/_generated/*`)

- Default canonical location: **primary checkout**.
- In session worktrees: `.edison/_generated` is symlinked back to the primary checkout’s `.edison/_generated`.
- Rationale: `_generated` is gitignored and should be shared so every worktree sees the same composed constitutions/guidelines/prompts.

### 4) “Meta-managed” arbitrary paths (`worktrees.sharedState.sharedPaths`)

Examples: `.claude/`, `.cursor/`, `.zen/`, `specs/`, `.specify/`, `.openspec/`, `.augment/`, and selected `.edison/*` subdirs.

- Canonical location: **meta worktree** (`<meta>/<path>`).
- In primary + session worktrees: those paths become **symlinks** pointing into the meta worktree.
- Rationale: tool/system prompt folders stay consistent across worktrees and across code branches.

## Git ignores / excludes (how noise is prevented)

Symlinked shared state must not show up as “untracked noise” in worktrees.

Edison writes ignore patterns into each checkout’s **worktree-local excludes**:

- Location: `<gitdir>/info/exclude` (note: for worktrees the gitdir is not necessarily `<checkout>/.git`)
- This is where Edison adds patterns like `.project/`, `.edison/_generated/`, and each configured shared path.

Important:

- Excludes affect only **untracked** files.
- Excludes do **not** hide changes to tracked files.

## Meta branch commit safety (commit guard)

The meta worktree installs a pre-commit hook (“commit guard”) that only allows commits for configured prefixes (e.g. `.project/tasks/`, `.project/qa/`, and sharedPaths you explicitly allow).

This keeps the meta branch “meta-only” even though it is a normal git worktree checkout.

## Setup / initialization

1) Configure shared state in `.edison/config/project.yaml`:
   - `worktrees.sharedState.mode: meta` (default)
   - `worktrees.sharedState.sharedPaths: [...]`
   - `worktrees.sharedState.commitGuard.allowPrefixes: [...]`
2) Initialize the meta worktree:
   - `edison git worktree-meta-init`
3) Create sessions normally:
   - `edison session create --id <sessionId>`

## Adding a new meta-managed folder

1) Add an entry to `worktrees.sharedState.sharedPaths` for the repo-root path (dir or file).
2) Copy the desired content into the meta worktree and commit it on `edison-meta` (subject to commitGuard).
3) Remove that content from code branches (so it is no longer tracked there).
4) Re-run `edison git worktree-meta-init` so primary + sessions pick up the symlink.

Safety note: Edison intentionally **skips symlinking** a sharedPath if that path is tracked in the checkout. This prevents “tracked directory replaced by symlink” surprises.

## Troubleshooting checklist

- `edison git worktree-meta-init --json` shows counts for:
  - `shared_paths_*_updated`
  - `shared_paths_*_skipped_tracked`
- If `*_skipped_tracked > 0`, remove that path from the code branch first (it’s still tracked).
- `ls -la <path>` should show symlinks in primary/session worktrees for shared state.
- `git worktree list` should show `_meta` and your session worktrees.

