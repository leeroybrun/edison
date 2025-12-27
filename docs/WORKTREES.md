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

### 1) Canonical shared state (`worktrees.sharedState.sharedPaths`)

`sharedPaths` is the single source of truth for what is shared via symlink between worktrees.

By default it includes:
- `.project/{tasks,qa,sessions,logs,archive}` (meta-managed)
- `.edison/_generated` (meta-managed; never committed)
- Tool/config folders like `.pal/`, `.claude/`, `.cursor/`, `.specify/`, `specs/`, `.openspec/`, etc.

### 2) Bootstrap configuration (`.edison/config/*`)

- Location: **tracked in code branches** (primary + session worktrees each have a real `.edison/config` directory from the branch checkout).
- Not symlinked by default.
- Rationale: Edison must be able to read config before it knows where/how to link the meta worktree.

If you want config to be shared across all worktrees, do it by editing config in your code branch and letting Git propagate it as normal code/config.

## Git ignores / excludes (how noise is prevented)

Symlinked shared state must not show up as “untracked noise” in worktrees.

Edison writes ignore patterns using **per-worktree excludes** so that meta/primary/session can have different noise policies.

- Mechanism: `git config --worktree core.excludesFile <path>`
- Edison writes patterns like `.project/`, `.edison/_generated/`, and shared-path symlink locations into that file.
- Git requirement: Edison enables `extensions.worktreeConfig=true` so per-worktree config is supported in repos with multiple worktrees.

Important:

- Excludes affect only **untracked** files.
- Excludes do **not** hide changes to tracked files.

## Meta branch commit safety (commit guard)

The meta worktree installs a pre-commit hook (“commit guard”) that only allows commits for:
- any configured `worktrees.sharedState.sharedPaths` entries (dirs/files) whose `targetRoot` is `shared` **and** `commitAllowed: true`
- plus any explicit extras in `worktrees.sharedState.commitGuard.allowPrefixes`

This keeps the meta branch “meta-only” even though it is a normal git worktree checkout.

## Recommended defaults + overriding sharedPaths

Edison ships a **recommended default** `worktrees.sharedState.sharedPaths` list (tool folders and `.edison/*` overlays).
Projects can:
- append new items (deep-merge list append): `sharedPaths: ["+", {path: "foo", scopes: ["primary","session"]}]`
- disable a default item by appending a matching path with `enabled: false`: `sharedPaths: ["+", {path: ".pal", enabled: false}]`
- avoid replacing defaults accidentally (do not set `sharedPaths: [...]` unless you mean to replace the entire list)

## Setup / initialization

1) Configure shared state in `.edison/config/project.yaml`:
   - `worktrees.sharedState.mode: meta` (default)
   - `worktrees.sharedState.sharedPaths: [...]`
   - `worktrees.sharedState.commitGuard.allowPrefixes: [...]`
2) Initialize the meta worktree:
   - `edison git worktree-meta-init`
3) Create sessions normally:
   - `edison session create --id <sessionId>`

If you're setting up a brand new project, `edison init` will guide you through these choices
and can bootstrap the meta worktree automatically when you enable worktrees.

## Adding a new meta-managed folder

1) Add an entry to `worktrees.sharedState.sharedPaths` for the repo-root path (dir or file).
2) Copy the desired content into the meta worktree and commit it on `edison-meta` (subject to commitGuard).
3) Remove that content from code branches (so it is no longer tracked there).
4) Re-run `edison git worktree-meta-init` so primary + sessions pick up the symlink.

## Important: `edison compose all` does NOT update git hooks

`edison compose all` regenerates composed artifacts under `.edison/_generated/` (constitutions, guidelines, etc).
It does **not** write `.git/hooks/pre-commit` because git hooks are **local to your checkout** and are not tracked.

To install/update the meta-branch commit guard hook after changing `sharedPaths` / `commitGuard` config, run:
- `edison git worktree-meta-init`

Safety notes:
- Running `edison git worktree-meta-init` is **idempotent** (it re-applies symlinks/excludes and rewrites the meta hook only if its content differs).
- Avoid `--recreate` unless you explicitly want a destructive rebuild of the meta branch/worktree.

Safety note: Edison intentionally **skips symlinking** a sharedPath if that path is tracked in the checkout. This prevents “tracked directory replaced by symlink” surprises.

## Troubleshooting checklist

- `edison git worktree-meta-init --json` shows counts for:
  - `shared_paths_*_updated`
  - `shared_paths_*_skipped_tracked`
- If `*_skipped_tracked > 0`, remove that path from the code branch first (it’s still tracked).
- `ls -la <path>` should show symlinks in primary/session worktrees for shared state.
- `git worktree list` should show `_meta` and your session worktrees.

