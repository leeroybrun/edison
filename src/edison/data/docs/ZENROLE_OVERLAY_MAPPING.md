# zenRole Project Overlay Mapping

This note explains how Edison keeps zenRole identifiers project-agnostic while letting each repository supply its own names through YAML overlays. Everything is configuration-driven—no hardcoded role strings—and the mapping lives alongside your project in `.edison/`.

## What are zenRoles

zenRoles are stable identifiers that tie a persona to its prompts, tools, and validation posture. Core agent specs (for example `feature-implementer.md` in `.edison/core/agents/`) reference zenRoles through template variables instead of fixed strings. This keeps the core catalog reusable while letting each project decide the exact role names it registers with Zen.

### How they work in Edison

1) Core content (agents, validators, orchestration manifests) declares `zenRole: "{{project.zenRoles.<id>}}"`.  
2) ConfigManager loads defaults from `edison.data.config/*.yaml`, then merges any overlays in `.edison/core/config/*.yaml` and finally the project overlays under `.edison/config/*.yml`.  
3) When prompts or manifests are composed, the template variable is resolved to the value defined in the project overlay. Missing entries fail fast so you notice gaps before execution.

## Project overlays (.edison/)

The `.edison/` directory is the project’s override layer. Within it, `.edison/config/*.yml` can replace or extend any core config. Because zenRole values must be YAML-driven, the overlay is the only place where project-specific role strings belong. This keeps Edison coherent across projects and prevents leaked, hardcoded names.

## Mapping zenRoles to overlay content

Define the project’s role names under `project.zenRoles` in your overlay. A minimal example:

```yaml
# .edison/config/project.yml
project:
  name: acme-web
  zenRoles:
    api-builder: acme-api-builder
    component-builder: acme-component-builder
    database-architect: acme-database-architect
    feature-implementer: acme-feature-implementer
    test-engineer: acme-test-engineer
    code-reviewer: acme-code-reviewer
```

How the mapping is applied:
- Core agent frontmatter references placeholders like `{{project.zenRoles.api-builder}}`.
- During composition, ConfigManager merges defaults → optional core overlays → project overlay and substitutes the placeholder with `acme-api-builder`.
- The resulting prompts, MCP configs, and orchestrator manifests use the project-specific names without modifying core files.

### Overlay precedence

1) Core defaults: `src/edison/data/config/*.yaml`  
2) Optional shared overrides: `.edison/core/config/*.yaml` (useful for org-wide defaults)  
3) Project overlay: `.edison/config/*.yml` (final authority for a repository)  

Later layers replace or extend earlier ones, so define zenRole strings in the project overlay to avoid surprises.

## Create custom zenRoles for a project

1) Pick a new identifier (e.g., `observability-analyst`) that matches how your agents will reference it.  
2) Add it to `.edison/config/project.yml` under `project.zenRoles`.  
3) Reference the placeholder in agent frontmatter or validator config: `zenRole: "{{project.zenRoles.observability-analyst}}"`.  
4) Run your normal composition workflow (e.g., `edison prompts compose`, `edison session start`, or pack installers). Those commands read the overlay and propagate the value everywhere.  
5) If you regenerate overlays using project scaffolding, review the generated stub to ensure your custom role remains present—never patch core files.

Because everything is YAML-driven, adding or renaming roles never requires code changes; you only adjust the overlay.

## Examples of common zenRole configurations

- **Standard web app**  
  ```yaml
  project:
    name: acme-web
    zenRoles:
      api-builder: acme-api-builder
      component-builder: acme-component-builder
      validator-security: acme-validator-security
      validator-performance: acme-validator-performance
  ```

- **Compliance-heavy services**  
  ```yaml
  project:
    name: fintech-edge
    zenRoles:
      feature-implementer: fintech-feature-implementer
      test-engineer: fintech-test-engineer
      validator-compliance: fintech-validator-compliance
      validator-privacy: fintech-validator-privacy
  ```

Guidelines:
- Keep names unique within your Zen deployment.  
- Store every role string in YAML overlays, never in code or templates.  
- Avoid project-specific prefixes in core files; use `{{project.zenRoles.*}}` placeholders instead.  
