from __future__ import annotations

from pathlib import Path

from edison.core.adapters.components.base import AdapterContext
from edison.core.adapters.components.commands import CommandComposer
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.config import ConfigManager


class _AdapterStub:
    def __init__(self, packs: list[str]) -> None:
        self._packs = packs

    def get_active_packs(self) -> list[str]:
        return self._packs


def _ctx(tmp_path: Path, *, packs: list[str]) -> AdapterContext:
    project_root = tmp_path
    project_dir = project_root / ".edison"
    user_dir = project_root / ".edison-user"
    core_dir = project_root / "core"
    bundled_packs_dir = project_root / "bundled_packs"
    user_packs_dir = user_dir / "packs"
    project_packs_dir = project_dir / "packs"

    for d in (
        project_dir,
        user_dir,
        core_dir,
        bundled_packs_dir,
        user_packs_dir,
        project_packs_dir,
        project_dir / "config",
    ):
        d.mkdir(parents=True, exist_ok=True)

    cfg_mgr = ConfigManager(project_root)
    writer = CompositionFileWriter(base_dir=project_root)
    adapter_stub = _AdapterStub(packs)

    return AdapterContext(
        project_root=project_root,
        project_dir=project_dir,
        user_dir=user_dir,
        core_dir=core_dir,
        bundled_packs_dir=bundled_packs_dir,
        user_packs_dir=user_packs_dir,
        project_packs_dir=project_packs_dir,
        cfg_mgr=cfg_mgr,
        config={},
        writer=writer,
        adapter=adapter_stub,
    )


def test_project_pack_template_overrides_bundled_pack(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, packs=["p1"])

    (ctx.bundled_packs_dir / "p1" / "templates" / "commands").mkdir(parents=True, exist_ok=True)
    (ctx.project_packs_dir / "p1" / "templates" / "commands").mkdir(parents=True, exist_ok=True)

    (ctx.bundled_packs_dir / "p1" / "templates" / "commands" / "x.md.template").write_text(
        "bundled", encoding="utf-8"
    )
    (ctx.project_packs_dir / "p1" / "templates" / "commands" / "x.md.template").write_text(
        "project-pack", encoding="utf-8"
    )

    composer = CommandComposer(ctx)
    resolved = composer._resolve_template("x.md.template")
    assert resolved == (ctx.project_packs_dir / "p1" / "templates" / "commands" / "x.md.template")


def test_user_template_overrides_pack_templates(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, packs=["p1"])

    (ctx.user_dir / "templates" / "commands").mkdir(parents=True, exist_ok=True)
    (ctx.project_packs_dir / "p1" / "templates" / "commands").mkdir(parents=True, exist_ok=True)
    (ctx.project_packs_dir / "p1" / "templates" / "commands" / "x.md.template").write_text(
        "project-pack", encoding="utf-8"
    )
    (ctx.user_dir / "templates" / "commands" / "x.md.template").write_text(
        "user", encoding="utf-8"
    )

    composer = CommandComposer(ctx)
    resolved = composer._resolve_template("x.md.template")
    assert resolved == (ctx.user_dir / "templates" / "commands" / "x.md.template")


def test_company_layer_template_overrides_pack_templates(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, packs=["p1"])

    company_dir = tmp_path / "company-layer"
    (company_dir / "config").mkdir(parents=True, exist_ok=True)
    (company_dir / "templates" / "commands").mkdir(parents=True, exist_ok=True)

    # Insert company layer before user.
    (ctx.project_dir / "config" / "layers.yaml").write_text(
        "layers:\n"
        "  roots:\n"
        "    - id: mycompany\n"
        f"      path: {company_dir.as_posix()}\n"
        "      before: user\n",
        encoding="utf-8",
    )

    (ctx.bundled_packs_dir / "p1" / "templates" / "commands").mkdir(parents=True, exist_ok=True)
    (ctx.bundled_packs_dir / "p1" / "templates" / "commands" / "x.md.template").write_text(
        "bundled", encoding="utf-8"
    )
    (company_dir / "templates" / "commands" / "x.md.template").write_text(
        "company", encoding="utf-8"
    )

    composer = CommandComposer(ctx)
    resolved = composer._resolve_template("x.md.template")
    assert resolved == (company_dir / "templates" / "commands" / "x.md.template")
