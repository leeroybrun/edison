from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from edison.core.config import ConfigManager
from edison.core.utils.io import ensure_directory
from edison.core.utils.text.templates import render_template_text
from edison.data import get_data_path

from .models import ShimDefinition


class ShimService:
    """Config-driven shim generation + env application.

    Shims are small wrapper executables placed early in PATH.
    They are generated into a repo-local directory so they can be used by:
    - Edison-launched orchestrator processes (Codex/Claude/etc.)
    - Any long-running shell/LLM process that opts in via `eval "$(edison shims env)"`
    """

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self._cfg_mgr = ConfigManager(repo_root=self.project_root)
        self._templates_dir = Path(get_data_path("templates", "shims"))

    # ---- config ---------------------------------------------------------
    def _config(self) -> dict[str, Any]:
        full = self._cfg_mgr.load_config(validate=False, include_packs=True)
        shims = full.get("shims", {}) or {}
        return shims if isinstance(shims, dict) else {}

    def enabled(self) -> bool:
        cfg = self._config()
        return cfg.get("enabled") is not False

    def output_dir(self) -> Path:
        cfg = self._config()
        out = cfg.get("output_dir") or ".edison/_generated/shims"
        p = Path(str(out))
        if not p.is_absolute():
            p = (self.project_root / p).resolve()
        return p

    def definitions(self) -> dict[str, ShimDefinition]:
        cfg = self._config()
        defs = cfg.get("definitions", {}) or {}
        if not isinstance(defs, dict):
            return {}

        out: dict[str, ShimDefinition] = {}
        for shim_id, raw in defs.items():
            if not isinstance(raw, dict):
                continue
            bin_name = str(raw.get("bin_name") or "")
            template = str(raw.get("template") or "")
            contexts = raw.get("contexts") or []
            if not isinstance(contexts, list):
                contexts = []
            context_list = [str(c) for c in contexts if str(c).strip()]
            config = raw.get("config") if isinstance(raw.get("config"), dict) else {}
            out[str(shim_id)] = ShimDefinition(
                id=str(shim_id),
                enabled=bool(raw.get("enabled", True)),
                description=str(raw.get("description") or ""),
                bin_name=bin_name,
                template=template,
                contexts=context_list,
                config=config,
            )
        return out

    # ---- rendering ------------------------------------------------------
    def _resolve_template_path(self, template: str) -> Path:
        # Allow project-local overrides for extensibility:
        #   .edison/templates/shims/<template>
        if not template:
            raise ValueError("Shim template is required.")

        candidate = Path(template)
        if candidate.is_absolute() and candidate.exists():
            return candidate

        # project override
        proj = (self.project_root / ".edison" / "templates" / "shims" / template).resolve()
        if proj.exists():
            return proj

        core = (self._templates_dir / template).resolve()
        if core.exists():
            return core

        raise FileNotFoundError(f"Shim template not found: {template}")

    def sync(self) -> list[Path]:
        """Render enabled shims to disk and return written paths."""
        if not self.enabled():
            return []

        out_dir = ensure_directory(self.output_dir())
        written: list[Path] = []

        for shim in self.definitions().values():
            if not shim.enabled:
                continue
            if not shim.bin_name:
                continue
            if not shim.template:
                continue

            template_path = self._resolve_template_path(shim.template)
            raw = template_path.read_text(encoding="utf-8")

            context = {
                "cfg": dict(shim.config),
                "shim": {
                    "id": shim.id,
                    "bin_name": shim.bin_name,
                    "description": shim.description,
                },
            }
            rendered = render_template_text(raw, context)

            out_path = (out_dir / shim.bin_name).resolve()
            ensure_directory(out_path.parent)
            out_path.write_text(rendered, encoding="utf-8")
            out_path.chmod(out_path.stat().st_mode | 0o111)
            written.append(out_path)

        self._write_activate_script(out_dir)
        return written

    def _write_activate_script(self, out_dir: Path) -> Path:
        """Write a small helper script that prints exports for POSIX shells."""
        out_dir = Path(out_dir)
        path = out_dir / "activate.sh"
        content = (
            "# Generated by Edison. Source this file in a POSIX shell.\n"
            "EDISON_SHIMS_DIR=\"$(CDPATH= cd -- \"$(dirname -- \"${BASH_SOURCE:-$0}\")\" && pwd)\"\n"
            "export EDISON_SHIMS_DIR\n"
            "case \":${PATH:-}:\" in\n"
            "  *\":${EDISON_SHIMS_DIR}:\"*) ;;\n"
            "  *) export PATH=\"${EDISON_SHIMS_DIR}:${PATH:-}\" ;;\n"
            "esac\n"
        )
        path.write_text(content, encoding="utf-8")
        path.chmod(path.stat().st_mode | 0o111)
        return path

    # ---- env helpers ----------------------------------------------------
    def apply_to_env(self, env: dict[str, str], *, context: str) -> dict[str, str]:
        """Return a modified env with shim dir prepended to PATH (fail-open)."""
        try:
            if not self.enabled():
                return env
            defs = [d for d in self.definitions().values() if d.applies_to(context)]
            if not defs:
                return env
            self.sync()
            shim_dir = str(self.output_dir())
            current = env.get("PATH") or ""
            if current.split(os.pathsep, 1)[0] == shim_dir:
                env["EDISON_SHIMS_DIR"] = shim_dir
                return env
            env["PATH"] = f"{shim_dir}{os.pathsep}{current}" if current else shim_dir
            env["EDISON_SHIMS_DIR"] = shim_dir
            return env
        except Exception:
            return env

    def env_snippet(self, *, shell: str = "sh", context: str = "shell", sync: bool = True) -> str:
        """Return a shell snippet to enable shims in the current process."""
        if sync:
            self.sync()
        shim_dir = str(self.output_dir())

        sh = (shell or "sh").lower()
        if sh in {"fish"}:
            return (
                f"set -gx EDISON_SHIMS_DIR {shim_dir!r};\n"
                f"if not contains -- $EDISON_SHIMS_DIR $PATH; set -gx PATH $EDISON_SHIMS_DIR $PATH; end;\n"
            )

        # POSIX (bash/zsh/sh)
        return (
            f'export EDISON_SHIMS_DIR="{shim_dir}";\n'
            'case ":${PATH:-}:" in\n'
            '  *":${EDISON_SHIMS_DIR}:"*) ;;\n'
            '  *) export PATH="${EDISON_SHIMS_DIR}:${PATH:-}" ;;\n'
            "esac\n"
        )

    def exec_with_shims(self, argv: list[str], *, context: str = "shell") -> int:
        """Run argv with shims applied to PATH and return the exit code."""
        if not argv:
            raise ValueError("argv is required")
        env = self.apply_to_env(os.environ.copy(), context=context)
        proc = subprocess.run(argv, env=env, cwd=str(self.project_root))
        return int(proc.returncode)

