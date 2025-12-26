---
name: feature-implementer
pack: ansible
overlay_type: extend
---

<!-- extend: tools -->

### Ansible Commands (when working on playbooks/roles)

```bash
# Lint (MANDATORY)
{{fn:ci_command("lint")}}

# Optional: YAML lint
{{fn:ci_command("yaml-lint")}}

# Module reference (MANDATORY before using a module)
ansible-doc ansible.builtin.<module>

# Validate playbooks
ansible-playbook --syntax-check <playbook.yml>
ansible-playbook --check --diff <playbook.yml>

# Role tests (if Molecule is present)
{{fn:ci_command("molecule")}}
```

<!-- /extend -->

<!-- extend: guidelines -->

### Ansible Patterns (Pack)

{{include-section:packs/ansible/guidelines/includes/ansible/ANSIBLE.md#critical_rules}}
{{include-section:packs/ansible/guidelines/includes/ansible/ANSIBLE.md#idempotency_requirements}}
{{include-section:packs/ansible/guidelines/includes/ansible/ANSIBLE.md#security_requirements}}
{{include-section:packs/ansible/guidelines/includes/ansible/ANSIBLE.md#modern_practices}}

<!-- /extend -->

