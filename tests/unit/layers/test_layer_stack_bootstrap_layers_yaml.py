from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.layers import resolve_layer_stack


def test_layers_yaml_inserts_company_before_user(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = isolated_project_env

    company = root / "company-layer"
    (company / "config").mkdir(parents=True)

    # Define company layer in project config/layers.yaml
    proj_cfg = root / ".edison" / "config"
    proj_cfg.mkdir(parents=True, exist_ok=True)
    (proj_cfg / "layers.yaml").write_text(
        "layers:\n"
        "  roots:\n"
        "    - id: mycompany\n"
        f"      path: {company.as_posix()}\n"
        "      before: user\n",
        encoding="utf-8",
    )

    stack = resolve_layer_stack(root)
    ids = [l.id for l in stack.layers]
    assert ids == ["mycompany", "user", "project"]


def test_layers_yaml_can_reference_other_extra_layers(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    a = root / "layer-a"
    b = root / "layer-b"
    (a / "config").mkdir(parents=True)
    (b / "config").mkdir(parents=True)

    proj_cfg = root / ".edison" / "config"
    proj_cfg.mkdir(parents=True, exist_ok=True)
    (proj_cfg / "layers.yaml").write_text(
        "layers:\n"
        "  roots:\n"
        "    - id: A\n"
        f"      path: {a.as_posix()}\n"
        "      before: user\n"
        "    - id: B\n"
        f"      path: {b.as_posix()}\n"
        "      after: A\n",
        encoding="utf-8",
    )

    stack = resolve_layer_stack(root)
    ids = [l.id for l in stack.layers]
    assert ids == ["A", "B", "user", "project"]


def test_layers_yaml_rejects_unknown_target_layer(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    company = root / "company-layer"
    (company / "config").mkdir(parents=True)

    proj_cfg = root / ".edison" / "config"
    proj_cfg.mkdir(parents=True, exist_ok=True)
    (proj_cfg / "layers.yaml").write_text(
        "layers:\n"
        "  roots:\n"
        "    - id: mycompany\n"
        f"      path: {company.as_posix()}\n"
        "      before: does-not-exist\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as excinfo:
        resolve_layer_stack(root)
    assert "unknown target layer" in str(excinfo.value).lower()
