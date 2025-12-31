# Shell Execution Wrapper - Include-Only File
<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: principles -->
## principles

Run shell commands via Edison whenever possible:

- Prefer `edison exec -- <command> [args...]` for command execution.
- This enables safety shims (when configured) and records audit events for executed commands.
- If you have a persistent shell, you may additionally enable shims once:
  - `edison shims sync`
  - `eval "$(edison shims env)"`

<!-- /section: principles -->

