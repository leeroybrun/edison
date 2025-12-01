# Manifest Schemas

Schemas for framework manifests and registry definitions.

## Schemas

| Schema | Purpose | Validated In |
|--------|---------|--------------|
| `manifest.schema.json` | Edison framework manifest | Tests |

## Usage

Manifest schemas define the structure of Edison's self-describing metadata:

- **manifest**: Framework manifest declaring available agents, guidelines, validators, and orchestration settings

## Related Code

- `.edison/_generated/constitutions/ORCHESTRATORS.md` - Project manifest
- `edison.core.composition.registries` - Registry management
