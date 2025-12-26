---
name: global
pack: ansible
overlay_type: extend
---

<!-- extend: tech-stack -->

## Ansible Technology Stack

### Linting: ansible-lint (BLOCKING when Ansible changes exist)

```bash
{{fn:ci_command("lint")}} > {{fn:evidence_file("lint")}} 2>&1
```

**Validation Points:**
- FQCN used (e.g., `ansible.builtin.*`)
- Shell/command tasks guarded with `creates`/`removes` + accurate `changed_when`
- No plaintext secrets; `no_log: true` for secret-bearing tasks

### Optional: YAML lint

```bash
{{fn:ci_command("yaml-lint")}} > {{fn:evidence_file("yaml-lint")}} 2>&1 || true
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

