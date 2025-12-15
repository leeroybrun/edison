# Git Workflow (Condensed, Mandatory)

## Git Checklist
- [ ] Safety: no force‑push to main; no `--no‑verify`; no destructive commands
- [ ] Conventional commit: `type(scope): description`
- [ ] Only staged relevant files; tests/lint pass before commit

## Safety
- Never force‑push main; never skip hooks; no destructive commands.
- Avoid `git commit --amend` except when explicitly requested or adding hook edits (verify authorship and that it’s not pushed).
- Do not modify repo-level signing settings. Never write `commit.gpgsign` in local/global config. If signing prompts would break CI or tests, pass per‑command flags (e.g., `git -c commit.gpgsign=false commit -m "..."`).

## Commits
- Conventional commits: `type(scope): description`.
- Commit when meaningful or at checkpoint boundaries (not on every file change).

## Do/Don’t
- Do: verify authorship, run tests/lint before commit.
- Don’t: amend others’ commits; push failing builds.

## Git-Optional vs Git-Required (Edison Core)
- Git-optional: Edison session inspection commands (e.g. `session status --json`) must succeed even when `AGENTS_PROJECT_ROOT` is not a git repository; worktree metadata is treated as best-effort and may be omitted or left unchanged.
- Git-required: Commands that create or manipulate worktrees (`session sync-git`, worktree archival/cleanup, git-based TDD enforcement) require a valid git repository; in non-git roots they must fail-closed or degrade with clear warnings instead of attempting git operations.

## Worktree isolation (new)
- Default session worktrees live in `../${PROJECT}-worktrees/<session-id>/` to isolate changes per session.
- Manage lifecycle with `edison git worktree-create|worktree-restore|worktree-archive|worktree-cleanup`. Archive before long pauses; cleanup removes abandoned worktrees after closure.
- `edison orchestrator start` (or `edison session create` when configured) will create or restore the external worktree automatically; stay inside that worktree for all session work.
- Never share a worktree across sessions; guard rails should reject mixed-session worktrees.