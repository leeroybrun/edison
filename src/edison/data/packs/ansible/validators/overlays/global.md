---
name: global
pack: ansible
overlay_type: extend
---

<!-- extend: tech-stack -->

## Ansible Technology Stack

### Linting: ansible-lint (BLOCKING when Ansible changes exist)

```bash
edison evidence status <task-id> --preset <preset>
edison evidence capture <task-id> --preset <preset>
```

**Validation Points:**
- FQCN used (e.g., `ansible.builtin.*`)
- Shell/command tasks guarded with `creates`/`removes` + accurate `changed_when`
- No plaintext secrets; `no_log: true` for secret-bearing tasks

### Optional: YAML lint

```bash
edison evidence status <task-id> --preset <preset>
edison evidence capture <task-id> --preset <preset>
```

<!-- /extend -->

<!-- section: AnsibleChecks -->

## Ansible-Specific Validation (when Ansible files are touched)

### Idempotency
- Ensure the second run would not report changes for stable state.
- Prefer declarative modules; avoid `shell` unless necessary and guarded.

### Security
- Secrets in vaults and never logged.
- `become` is scoped, justified, and minimal.

### Maintainability
- Clear task names, role boundaries, and variable namespacing.
- Templates validated (`validate:`) where possible.

<!-- /section: AnsibleChecks -->
