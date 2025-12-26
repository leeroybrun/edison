# Memory

Edison’s core workflow state (tasks/QA/sessions) lives under `.project/` and is always the source of truth. The **memory** system is optional, provider-driven, and designed to be **fail-open**: when providers are unavailable or misconfigured, Edison keeps working.

## Concepts

- **Providers** (`memory.providers.*`): optional integrations that can `search` and `save` memory.
- **Pipelines** (`memory.pipelines.*`): event-driven workflows run via `edison memory run` (e.g. on `session-end`) to persist structured “session insights” and/or trigger provider indexing.
- **File fallback** (`file-store` provider): persists memory artifacts under `.project/memory/` so memory survives even when external providers aren’t available.

## Quick Start (File-Based Fallback)

1) Enable memory + the file-store provider in `.edison/config/memory.yaml`:

```yaml
memory:
  enabled: true
  providers:
    file:
      kind: file-store
      enabled: true
```

2) Run a pipeline manually (example below) or call `save_structured` via `edison memory run`:

```bash
edison memory run --event session-end --session sess-001 --best-effort
```

## File Store Layout

When `file-store` is enabled, Edison writes to the configured `memory.paths.root` (default: `.project/memory/`):

- `codebase_map.json`: lightweight map of files → notes (best-effort, derived from evidence + follow-up context).
- `patterns.md`: appended bullet list of patterns (deduped).
- `gotchas.md`: appended bullet list of gotchas (deduped).
- `session_insights/<session-id>.json`: structured session insights records.

## Providers

### Episodic Memory (CLI)

Install (one of):

- As a Claude Code plugin: `/plugin install episodic-memory@superpowers-marketplace`
- As a CLI: `npm install -g episodic-memory` (or use `npx -y episodic-memory ...`)

Then configure the `episodic-memory` executable (on your `PATH`) as an `external-cli-text` provider:

```yaml
memory:
  enabled: true
  providers:
    episodic:
      kind: external-cli-text
      command: episodic-memory
      searchArgs: ["search", "{query}"]
      timeoutSeconds: 10
```

Optional indexing (run by a pipeline step `provider-index`):

```yaml
memory:
  providers:
    episodic:
      kind: external-cli-text
      command: episodic-memory
      searchArgs: ["search", "{query}"]
      indexArgs: ["sync"]
```

### Episodic Memory (MCP)

If you run episodic memory as an MCP server, configure the MCP server and then add an `mcp-tools` provider.

`.edison/config/mcp.yaml`:

```yaml
mcp:
  servers:
    episodic-memory:
      command: episodic-memory-mcp-server
      args: []
      env: {}
```

`.edison/config/memory.yaml`:

```yaml
memory:
  enabled: true
  providers:
    episodic:
      kind: mcp-tools
      serverId: episodic-memory
      searchTool: episodic_memory_search
      # Optional, for full-conversation retrieval if you wire it later:
      # readTool: episodic_memory_show
      responseFormat: json
      # Optional override (values may include {query} and {limit})
      searchArguments:
        query: "{query}"
        limit: "{limit}"
        response_format: json
```

### Graphiti (Python)

Edison’s `graphiti-python` provider expects a Python module exposing a `GraphitiMemory` class (or your configured class) with an async API:

- `get_relevant_context(query, num_results=..., include_project_context=...)`
- optional `get_session_history(limit=...)`
- `saveMethod` (text) and optional `saveStructuredMethod` (dict)

Example `.edison/config/memory.yaml`:

```yaml
memory:
  enabled: true
  providers:
    graphiti:
      kind: graphiti-python
      module: graphiti_memory
      class: GraphitiMemory
      specDir: "{PROJECT_MANAGEMENT_DIR}/memory/graphiti"
      groupIdMode: project
      includeProjectContext: true
      includeSessionHistory: true
      sessionHistoryLimit: 3
      saveMethod: save_pattern
      saveStructuredMethod: save_structured_insights
      saveTemplate: "{summary}"
```

## Pipelines

Pipelines are keyed by event id and run via `edison memory run --event <event>`.

Example: structured session insights persisted to Graphiti (primary) and file-store (fallback), plus episodic indexing:

```yaml
memory:
  enabled: true
  providers:
    graphiti:
      kind: graphiti-python
      enabled: true
      module: graphiti_memory
      class: GraphitiMemory
      specDir: "{PROJECT_MANAGEMENT_DIR}/memory/graphiti"
      saveStructuredMethod: save_structured_insights
    file:
      kind: file-store
      enabled: true
    episodic:
      kind: external-cli-text
      enabled: true
      command: episodic-memory
      searchArgs: ["search", "{query}"]
      indexArgs: ["sync"]
  pipelines:
    session-end:
      enabled: true
      steps:
        - id: extract
          kind: session-insights-v1
          outputVar: insights
        - id: save-graphiti
          kind: provider-save-structured
          provider: graphiti
          inputVar: insights
        - id: save-file
          kind: provider-save-structured
          provider: file
          inputVar: insights
        - id: index-episodic
          kind: provider-index
          provider: episodic
```

Run manually:

```bash
edison memory run --event session-end --session sess-001
```

## Hooks (Session End)

The bundled `session-cleanup` hook can optionally run the `session-end` memory pipeline.

Enable it via `.edison/config/hooks.yaml`:

```yaml
hooks:
  definitions:
    session-cleanup:
      config:
        run_memory_pipeline: true
        memory_pipeline_event: session-end
        memory_best_effort: true
```
