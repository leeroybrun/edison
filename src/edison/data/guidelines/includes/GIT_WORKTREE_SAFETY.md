# Worktree + Git Safety - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: worktree-confinement -->
## Worktree Confinement (CRITICAL)
- **All code changes must happen inside the session worktree directory** (never in the primary checkout).
- After creating/resuming a session, run `edison session status --json`, read `git.worktreePath`, then `cd <worktreePath>` and stay there.
- Edison shares local state into each worktree via symlinks: `{{fn:project_management_dir}}/` (tasks, QA, logs, archive, sessions), `{{fn:project_config_dir}}/_generated` (composed constitutions/guidelines), and any configured `worktrees.sharedState.sharedPaths`. If these links are missing, task/QA commands may appear “empty” and start prompts/constitutions may be absent inside the worktree.
- **Session runtime state is local-only.** Do not commit `{{fn:sessions_root}}/` or `{{fn:project_management_dir}}/.session-id` (they should be gitignored).
<!-- /section: worktree-confinement -->

<!-- section: worktree-isolation -->
## Worktree Isolation (Sessions)
- Default session worktrees live at `{{config.worktrees.pathTemplate}}` (config: `worktrees.pathTemplate`).
- Create/restore via `edison session create` / `edison orchestrator start` / `edison git worktree-*` (do not DIY worktrees).
- If `worktrees.sharedState.mode=meta`, initialize shared state with `edison git worktree-meta-init`. The meta worktree path is reserved for a git worktree (do not pre-create it as a plain directory). If you override `worktrees.baseDirectory`, also override `worktrees.sharedState.metaPathTemplate` to keep them aligned and avoid collisions.
- Primary checkout safety is enforced: Edison must never switch the primary checkout branch during worktree operations.
<!-- /section: worktree-isolation -->

<!-- section: worktree-base-ref -->
## Worktree Base Ref Selection
- Default behavior: create the session worktree from the **current primary checkout HEAD** (not implicitly `main`).
- To force a fixed base ref (e.g. always `main`): set `worktrees.baseBranchMode: fixed` + `worktrees.baseBranch: main` (or just `worktrees.baseBranch: main`).
- Per command override:
  - `edison session create --base-branch <ref>`
  - `edison git worktree-create <session-id> --branch <ref>`
<!-- /section: worktree-base-ref -->

<!-- section: git-safety -->
## Git Safety (Non-Negotiable)
- **Never switch branches in the primary checkout.** Edison/LLMs MUST NOT run `git checkout` / `git switch` in the primary worktree.
- **Branch creation/deletion is restricted.** Only create/delete branches via Edison session/worktree commands unless the user explicitly asks otherwise.
<!-- /section: git-safety -->

<!-- section: agent-git-safety -->
## Git Safety (Agents)
- Do not run `git checkout` / `git switch` / `git branch` (or create branches) as part of implementation unless explicitly asked by the user.
- Use Edison session/worktree commands for any branch/worktree lifecycle.
<!-- /section: agent-git-safety -->
