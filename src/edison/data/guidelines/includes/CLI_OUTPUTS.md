# CLI Output Preference - Include-Only File
<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: principles -->
## principles

Default to human-readable CLI output.

- Prefer plain text/Markdown output when reading command results inside an LLM conversation.
- Use `--json` only when you need structured output for tools/scripts or when explicitly requested.
<!-- /section: principles -->

<!-- section: orchestrator -->
## orchestrator

Orchestrators should default to non-JSON output when making decisions and briefing sub-agents. Only use `--json` when piping into tooling or when you need exact structured fields.
<!-- /section: orchestrator -->

<!-- section: agent -->
## agent

Agents should default to non-JSON output while implementing; only use `--json` when required by a specific workflow step or when the orchestrator requests structured output.
<!-- /section: agent -->

<!-- section: validator -->
## validator

Validators should default to non-JSON output while reviewing. Use `--json` only when it is explicitly needed for structured extraction or reporting.
<!-- /section: validator -->

