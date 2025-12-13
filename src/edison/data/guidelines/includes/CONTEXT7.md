# Context7 - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: agent -->
### Resolve Library ID
Use Context7 to resolve the canonical library ID:
```
mcp__context7__resolve_library_id({ libraryName: "<package-name>" })
```

### Get Current Documentation
Fetch up-to-date docs before coding or reviewing:
```
mcp__context7__get_library_docs({
  context7CompatibleLibraryID: "/<org>/<library>",
  mode: "code",
  topic: "<relevant-topic>",
  page: 1
})
```

- Check `config/context7.yaml` for active versions/topics used by this repo.
<!-- /section: agent -->

<!-- section: validator -->
### Knowledge Refresh (When Applicable)
If the change touches any configured post-training package, refresh docs via Context7 and record evidence as required by workflow.
<!-- /section: validator -->

<!-- section: orchestrator -->
### Knowledge Refresh Enforcement
If a task touches configured post-training packages, ensure the assigned agent refreshes Context7 docs and produces the required evidence markers before `wip → done`.
<!-- /section: orchestrator -->


