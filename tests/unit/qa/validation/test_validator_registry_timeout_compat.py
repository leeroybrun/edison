from __future__ import annotations

from pathlib import Path


def test_validator_registry_uses_validation_timeout_as_fallback(isolated_project_env: Path) -> None:
    cfg = isolated_project_env / ".edison" / "config" / "validation.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        """
validation:
  execution:
    timeout: null
  timeout: 4242
  validators:
    demo:
      name: Demo
      engine: pal-mcp
      wave: global
""".lstrip(),
        encoding="utf-8",
    )

    from edison.core.registries.validators import ValidatorRegistry

    reg = ValidatorRegistry(project_root=isolated_project_env)
    assert reg.default_timeout == 4242
    demo = reg.get("demo")
    assert demo is not None
    assert demo.timeout == 4242
