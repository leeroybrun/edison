# Pal role → overlay mapping

This document explains how Edison maps a **palRole** (a role identifier used for delegation and prompt selection) to the **project overlay** content that gets composed into prompts and validator runs.

## What are palRoles?

- **palRoles** are stable, human-readable identifiers for roles used by delegated execution (Pal MCP / clink).
- They let Edison keep its core prompts generic while allowing each project to map roles to its own overlays and capabilities.
- palRoles are configured in YAML, not hardcoded in code.

## How they work

At a high level:

- Edison composes core + packs + project overlays into prompt artifacts.
- When Edison needs to delegate (or select a role-specific prompt), it uses a palRole (for example `agent-api-builder` or `validator-security`).
- The palRole determines which overlay content and rules are included.

## Project overlays

Projects override role mappings in `.edison/config/project.yaml`:

```yaml
project:
  palRoles:
    api-builder: "agent-api-builder"
    code-reviewer: "agent-code-reviewer"
```

Those mappings are referenced from agent prompt frontmatter via template variables, for example:

```yaml
palRole: "{{project.palRoles.api-builder}}"
```

## Mapping behavior

- **Core** defines default `project.palRoles` values.
- **Project overlays** can override them to match local conventions.
- Packs may add additional role-aware content; the active packs are always part of the composed prompt.

## Create custom palRoles

To define custom palRoles:

1. Add/override mappings in `.edison/config/project.yaml`.
2. Reference them from agent frontmatter using template variables.
3. Re-run `edison compose all` to regenerate artifacts.

## Examples

```yaml
project:
  palRoles:
    my-custom-agent: "agent-my-custom-agent"
```

