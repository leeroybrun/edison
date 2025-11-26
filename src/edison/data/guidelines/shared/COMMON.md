# Shared Common Instructions (MANDATORY)

These instructions apply to **all agents and validators**. Read alongside role-specific constitutions and guidelines.

## Context7 Knowledge Refresh (MANDATORY)
- Your training data is stale for post-training packages. Always refresh docs before coding or validating.
- Resolve the library ID, then pull current docs via Context7 MCP:
```ts
const pkgId = await mcp__context7__resolve-library-id({ libraryName: "<package-name>" })
await mcp__context7__get-library-docs({
  context7CompatibleLibraryID: pkgId,
  topic: "<relevant topics>",
})
```
- Check `config/context7.yml` for active versions. Expect major diffs in **Next.js 16**, **React 19**, **Tailwind CSS 4**, **Prisma 6**, and other post-training packages.
- Create Context7 evidence markers as required in `guidelines/shared/CONTEXT7.md`; guards block readiness without them.
- Follow the full workflow in `guidelines/shared/CONTEXT7.md` when package docs are involved.

## Configuration-First Guardrail
- No hardcoded values; read behavior from YAML config and reuse existing utilities before adding new ones.
- Keep instructions DRY and coherent—prefer shared guidelines over repeating blocks in role files.

## TDD Is Non-Negotiable
- Apply RED → GREEN → REFACTOR for every change.
- Capture evidence of the sequence in implementation or validation reports; see `guidelines/shared/TDD.md` for expectations.
