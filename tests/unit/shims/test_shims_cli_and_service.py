from __future__ import annotations

from pathlib import Path

from edison.core.shims import ShimService


def test_shim_service_sync_writes_git_shim(tmp_path: Path, isolated_project_env) -> None:
    svc = ShimService(project_root=tmp_path)
    written = svc.sync()
    out_dir = svc.output_dir()
    assert out_dir.exists()
    assert (out_dir / "git").exists()
    assert (out_dir / "activate.sh").exists()
    assert any(p.name == "git" for p in written)


def test_shim_service_env_snippet_contains_output_dir(tmp_path: Path, isolated_project_env) -> None:
    svc = ShimService(project_root=tmp_path)
    snippet = svc.env_snippet(shell="sh", sync=True)
    assert str(svc.output_dir()) in snippet

