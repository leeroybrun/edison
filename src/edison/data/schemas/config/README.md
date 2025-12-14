# Configuration Schemas

Schemas for validating Edison configuration files and settings.

## Schemas

| Schema | Purpose | Validated In |
|--------|---------|--------------|
| `config.schema.json` | Main edison.yaml/defaults.yaml | Production: `ConfigManager` |
| `delegation-config.schema.json` | delegation routing rules (YAML) | Production: `ConfigManager` (merged config) |
| `delegation.schema.json` | delegation.yaml structure | Tests |
| `orchestrator-config.schema.json` | Orchestrator profiles | Production: `OrchestratorConfig.validate()` |
| `pack.schema.json` | Tech pack definitions | Production: `validate_pack()` |
| `state-machine-rich.schema.json` | State machine configuration | Production: `load_statemachine()` |

## Usage

Configuration schemas ensure that YAML/JSON configuration files conform to expected structures:

- **config**: Root Edison configuration merged from defaults and project settings
- **delegation-config**: File pattern rules for agent delegation
- **delegation**: Delegation workflow definitions
- **orchestrator-config**: Multi-profile orchestrator settings
- **pack**: Technology pack metadata and overlays
- **state-machine-rich**: Extended state machine with rich outputs

## Related Code

- `edison.core.config.manager.ConfigManager`
- `edison.core.config.domains.orchestrator.OrchestratorConfig`
- `edison.core.composition.packs.validate_pack()`
- `edison.core.composition.output.state_machine.load_statemachine()`
