# Edison Hook Templates

Templates for Claude Code hook scripts. Each template is Bash rendered via Jinja and expects JSON on `stdin` (from Claude) plus Edison CLI env. Replace `{{ id }}`, `{{ type }}`, and `{{ description }}` when instantiating. Optional `config` values toggle sections without breaking rendering.

## Templates
- `inject-session-context.sh.template` (UserPromptSubmit): emits current session/worktree/task/pack context before Claude reads the prompt.
- `inject-task-rules.sh.template` (UserPromptSubmit): when touched files match configured patterns, injects rule snippets for the current task state.
- `remind-tdd.sh.template` (PreToolUse): non-blocking RED/GREEN/REFACTOR reminder for Write/Edit tools, scoped to selected task states and skipping test files optionally.
- `commit-guard.sh.template` (PreToolUse): gate git commits run via Bash tool; can enforce passing tests and coverage thresholds and block with exit 1.
- `auto-format.sh.template` (PostToolUse): auto-runs configured formatters for matching Write/Edit file paths.
- `session-init.sh.template` (SessionStart): announces session start and echoes session id.
- `session-cleanup.sh.template` (SessionEnd): session teardown.
- `compaction-reminder.sh.template` (PreCompact): reminds agent to re-read its constitution after context compaction.

## Config knobs
- Booleans and lists are all optional and default to safe no-ops.
- Common keys used across templates: `config.include_*`, `config.file_patterns`, `config.rules_by_state`, `config.only_for_states`, `config.skip_test_files`, `config.require_tests_pass`, `config.require_coverage`, `config.coverage_threshold`, `config.tools`, `config.save_logs`.

## Testing
Run `{{function:ci_command("test")}}` (repo equivalent) to ensure templates render with/without config, produce valid shell, and respect blocking behavior hints.
