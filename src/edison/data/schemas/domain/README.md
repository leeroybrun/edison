# Domain Schemas

Core framework entities that represent the primary business objects in Edison workflows.

## Schemas

| Schema | Purpose | Validated In |
|--------|---------|--------------|
| `session.schema.yaml` | Session state and metadata | Tests, metadata validation |
| `task.schema.yaml` | Task definitions and status tracking | Tests, state machine alignment |
| `qa.schema.yaml` | QA workflow and validation state | Tests |

## Usage

These schemas define the structure of Edison's core domain objects:

- **Session**: Tracks active work sessions, worktrees, and associated tasks
- **Task**: Represents individual work items with status, TDD evidence, and dependencies
- **QA**: Defines quality assurance workflow states and validation results

## Related Code

- `edison.core.session` - Session management
- `edison.core.task` - Task lifecycle
- `{{config.session.paths.root}}/` - Session files in project directories
- `{{config.tasks.paths.root}}/` - Task files in project directories
