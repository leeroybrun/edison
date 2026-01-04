from __future__ import annotations

from pathlib import Path

from edison.core.utils.io.yaml import iter_yaml_files


def test_iter_yaml_files_prefers_yaml_when_both_extensions_exist(tmp_path: Path) -> None:
    d = tmp_path / "config"
    d.mkdir(parents=True, exist_ok=True)

    (d / "validation.yml").write_text("validation:\n  a: 1\n", encoding="utf-8")
    (d / "validation.yaml").write_text("validation:\n  a: 2\n", encoding="utf-8")
    (d / "other.yml").write_text("x: 1\n", encoding="utf-8")
    (d / "z.yaml").write_text("z: 1\n", encoding="utf-8")

    files = iter_yaml_files(d)
    names = [p.name for p in files]

    assert "validation.yaml" in names
    assert "validation.yml" not in names

