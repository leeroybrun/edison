---
name: code-reviewer
pack: ansible
overlay_type: extend
---

<!-- extend: guidelines -->

### Ansible Review Focus (Pack)

- Enforce **FQCN** (`ansible.builtin.*`, `community.*`) and validate module params via `ansible-doc`.
- Flag any `shell`/`command` usage missing `creates`/`removes` or accurate `changed_when`/`failed_when`.
- Require `no_log: true` and vault usage for any secret-bearing tasks.
- Require scoped `become` and explicit file permissions for sensitive files.

{{include-section:packs/ansible/guidelines/includes/ansible/ANSIBLE.md#code_quality_checklist}}

<!-- /extend -->

