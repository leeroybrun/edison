# Edison Core Schemas

JSON Schema definitions that validate Edison configuration and data payloads.

**Schema drafts used**:
- **Draft 2020-12**: `config/`, `domain/`, `adapters/`, `manifests/`
- **Draft-07**: `reports/` (currently)

## Directory Structure

```
schemas/
├── domain/                  # Core framework entities
│   ├── session.schema.json  # Session state and metadata
│   ├── task.schema.json     # Task definitions and status
│   └── qa.schema.json       # QA workflow state
├── config/                  # Configuration validation
│   ├── config.schema.json   # edison.yaml/defaults.yaml
│   ├── delegation-config.schema.json
│   ├── delegation.schema.json
│   ├── orchestrator-config.schema.json
│   ├── pack.schema.json     # Tech pack definitions
│   └── state-machine-rich.schema.json
├── reports/                 # Agent output formats
│   ├── implementation-report.schema.json
│   ├── validator-report.schema.json
│   └── delegation-report.schema.json
├── adapters/                # IDE adapter schemas
│   ├── claude-agent.schema.json
│   └── claude-agent-config.schema.json
└── manifests/               # Framework manifests
    └── manifest.schema.json
```

## Categories

### Domain (`domain/`)
Core business objects: sessions, tasks, QA workflows. These define the primary entities that Edison manages.

### Config (`config/`)
Configuration file validation. Used in production by `ConfigManager`, `OrchestratorConfig`, and pack validation.

### Reports (`reports/`)
Structured output formats for validators and delegation results.

### Adapters (`adapters/`)
IDE-specific agent definitions and configurations for Claude, Cursor, etc.

### Manifests (`manifests/`)
Framework self-describing metadata and registry definitions.

## Usage

```python
from edison.core.schemas import load_schema, validate_payload

# Load a schema
schema = load_schema("config/config.schema.json")

# Validate a payload
validate_payload(config_dict, "config/config.schema.json")
```

## Schema Guidelines

1. **Match the family’s draft**:
   - `config/`, `domain/`, `adapters/`, `manifests/` → `"$schema": "https://json-schema.org/draft/2020-12/schema"`
   - `reports/` → `"$schema": "http://json-schema.org/draft-07/schema#"`
2. **Strict validation**: Set `additionalProperties: false` to catch typos
3. **Project-agnostic**: Core schemas must not contain project-specific terms
4. **Use placeholders**: Use `{PROJECT_NAME}` for customizable paths
