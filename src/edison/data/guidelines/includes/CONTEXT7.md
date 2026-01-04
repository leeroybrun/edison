# Context7 - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: workflow -->
Use Context7 to refresh your knowledge **before** implementing or validating when work touches any configured post-training package.

- Project overrides live in `{{fn:project_config_dir}}/config/context7.yaml`.
- To view the merged effective Context7 configuration (core → packs → user → project), run: `edison config show context7 --format yaml`.
- If the task/change does not touch any configured package, do not spend context on Context7.
- When required, record evidence using the project's configured evidence markers/locations (don’t invent new file names).
<!-- /section: workflow -->

<!-- section: agent -->
## Context7 Knowledge Refresh (MANDATORY)

### Resolve Library ID
Use Context7 to resolve the canonical library ID:
```
mcp__context7__resolve-library-id({
  libraryName: "<package-name>",
  query: "<what you are trying to do>"
})
```

### Get Current Documentation
Fetch up-to-date docs before coding or reviewing:
```
mcp__context7__query-docs({
  libraryId: "/<org>/<library>",
  query: "<relevant-topic>"
})
```

- Check `{{fn:project_config_dir}}/config/context7.yaml` for active versions/topics used by this repo.
<!-- /section: agent -->

<!-- section: validator -->
### Knowledge Refresh (When Applicable)
If the change touches any configured post-training package, refresh docs via Context7 and record evidence as required by workflow.
<!-- /section: validator -->

<!-- section: orchestrator -->
### Knowledge Refresh Enforcement
If a task touches configured post-training packages, ensure the assigned agent refreshes Context7 docs and produces the required evidence markers before `{{fn:semantic_state("task","wip")}} → {{fn:semantic_state("task","done")}}`.

### Context7 Error Handling
When `edison task ready` fails with Context7 errors:
1. Review the error message—it shows detected packages and missing markers
2. Check if detection is correct: `edison config show context7 --format yaml`
3. If correct: have the agent create Context7 evidence markers
4. If false positive: use `--skip-context7` bypass with justification

### Bypass Flag (`--skip-context7`)
For verified false positives only:
```bash
edison task ready <task-id> --skip-context7
```
- Prints a loud warning to stderr
- Records audit trace in session tracking
- Should be rare—most Context7 detections are legitimate
<!-- /section: orchestrator -->
