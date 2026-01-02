# PALROLE Overlay Mapping (Pal / clink)

This document explains how **Pal roles** map to **system prompt files**, and how Edison applies **project overlays** when generating prompts.

## What are “roles”?

In Pal, a **role** is a named prompt profile (for example: `default`, `planner`, `codereviewer`, or any **custom** role your project defines).

Edison uses role names to:
- select the right guideline/rule subsets for that role
- generate prompt files with stable names
- keep prompt selection deterministic across CLI clients

## Prompt file conventions (agent-/validator-)

Edison writes Pal prompts using filename conventions so roles are obvious:
- `agent-<role>.txt` for agent-style prompts
- `validator-<name>.txt` for validator prompts

These conventions are configured under `pal.cli_clients` and are used when syncing prompts.

## Where prompts live (.pal/systemprompts/clink)

When you run composition/sync, Pal prompt artifacts are written under:

```
.pal/conf/systemprompts/clink/project/
```

The generated files in that folder are what Pal (via **clink**) discovers and loads as system prompts.

## Project configuration (YAML/JSON)

Role mappings are driven by configuration, typically in YAML (or JSON-equivalent structures):
- `{{PROJECT_EDISON_DIR}}/config/pal.yaml` (project overrides)
- `{{PROJECT_EDISON_DIR}}/config/*.yml` / `*.yaml` overlays as needed

Key areas:
- `pal.roles`: defines role-specific guideline/rule/packs selection
- `pal.cli_clients`: defines how prompt files are named and where they are written

## Overlay behavior

Edison treats core prompts as the baseline and applies project overlays on top so you can:
- add new roles without editing core
- tune role-specific selection for your project
- keep generated prompt files stable and reviewable in git

## Examples

Minimal example role configuration (YAML):

```yaml
pal:
  enabled: true
  roles:
    default: {}
    planner:
      guidelines: ["architecture", "design", "planning"]
    codereviewer:
      guidelines: ["quality", "security", "performance"]
  cli_clients:
    roles:
      prefixes:
        agent: "agent-"
        validator: "validator-"
```

Adding a **custom** role:

```yaml
pal:
  roles:
    project-api-builder:
      guidelines: ["api-design", "validation", "error-handling"]
      rules: ["validation", "implementation"]
      packs: ["fastify"]
```

