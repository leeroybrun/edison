from __future__ import annotations

from pathlib import Path


def test_validator_registry_default_timeout_is_6000(isolated_project_env: Path) -> None:
    from edison.core.registries.validators import ValidatorRegistry

    reg = ValidatorRegistry(project_root=isolated_project_env)
    assert reg.default_timeout == 6000

