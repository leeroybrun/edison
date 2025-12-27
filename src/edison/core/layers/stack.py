from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from edison.core.utils.merge import deep_merge
from edison.core.utils.io import read_yaml
from edison.core.utils.paths import get_project_config_dir, get_user_config_dir
from edison.data import get_data_path

from edison.core.packs.model import PackRoot


@dataclass(frozen=True)
class LayerSpec:
    """A single overlay layer root (e.g., company, user, project)."""

    id: str
    path: Path


@dataclass(frozen=True)
class LayerStack:
    """Resolved layer stack for Edison extensibility."""

    repo_root: Path
    core_dir: Path
    core_config_dir: Path
    bundled_packs_dir: Path
    layers: tuple[LayerSpec, ...]  # low → high
    project_local_config_dir: Path

    def layer_by_id(self, layer_id: str) -> Optional[LayerSpec]:
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        return None

    def pack_roots(self) -> tuple[PackRoot, ...]:
        """Return pack roots in low→high precedence order."""
        roots: List[PackRoot] = [PackRoot(kind="bundled", path=self.bundled_packs_dir)]
        for layer in self.layers:
            roots.append(PackRoot(kind=layer.id, path=layer.path / "packs"))
        return tuple(roots)

    def config_dirs(self) -> List[Path]:
        """Return config directories in low→high precedence order (excluding env)."""
        dirs: List[Path] = [self.core_config_dir]
        for layer in self.layers:
            dirs.append(layer.path / "config")
        dirs.append(self.project_local_config_dir)
        return dirs


def _layers_yaml_paths(
    *,
    core_config_dir: Path,
    user_dir: Path,
    project_dir: Path,
    project_local_config_dir: Path,
) -> List[Path]:
    return [
        core_config_dir / "layers.yaml",
        user_dir / "config" / "layers.yaml",
        project_dir / "config" / "layers.yaml",
        project_local_config_dir / "layers.yaml",
    ]


def _load_layers_bootstrap_cfg(
    *,
    core_config_dir: Path,
    user_dir: Path,
    project_dir: Path,
    project_local_config_dir: Path,
) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for path in _layers_yaml_paths(
        core_config_dir=core_config_dir,
        user_dir=user_dir,
        project_dir=project_dir,
        project_local_config_dir=project_local_config_dir,
    ):
        if not path.exists():
            continue
        data = read_yaml(path, default={}, raise_on_error=True)
        if isinstance(data, dict):
            merged = deep_merge(merged, data)
    return merged


def _expand_layer_path(raw: str, *, repo_root: Path) -> Path:
    s = os.path.expandvars(str(raw)).strip()
    p = Path(s).expanduser()
    if not p.is_absolute():
        # Relative paths are treated as repo-relative for portability.
        p = (repo_root / p).resolve()
    return p.resolve()


def _parse_extra_layers(cfg: Dict[str, Any], *, repo_root: Path) -> List[Dict[str, Any]]:
    layers_cfg = cfg.get("layers") if isinstance(cfg.get("layers"), dict) else {}
    roots = layers_cfg.get("roots", []) if isinstance(layers_cfg, dict) else []
    if not isinstance(roots, list):
        return []
    parsed: List[Dict[str, Any]] = []
    for item in roots:
        if isinstance(item, str):
            # Allow merge marker strings from merge_arrays ("+", "=").
            continue
        if not isinstance(item, dict):
            continue
        layer_id = str(item.get("id") or "").strip()
        path_raw = item.get("path")
        if not layer_id or not isinstance(path_raw, str) or not path_raw.strip():
            continue
        parsed.append(
            {
                "id": layer_id,
                "path": _expand_layer_path(path_raw, repo_root=repo_root),
                "before": (str(item.get("before")).strip() if item.get("before") else None),
                "after": (str(item.get("after")).strip() if item.get("after") else None),
                "enabled": bool(item.get("enabled", True)),
            }
        )
    return parsed


def _insert_layer(
    base: List[LayerSpec],
    spec: LayerSpec,
    *,
    before: Optional[str],
    after: Optional[str],
) -> None:
    if before and after:
        raise ValueError(f"Layer '{spec.id}' cannot specify both before and after.")

    target = before or after or "user"
    try:
        idx = next(i for i, l in enumerate(base) if l.id == target)
    except StopIteration as exc:
        raise ValueError(f"Layer '{spec.id}' references unknown target layer '{target}'.") from exc

    if after:
        idx += 1
    base.insert(idx, spec)


def resolve_layer_stack(repo_root: Path) -> LayerStack:
    """Resolve the Edison layer stack for a repository root.

    Loads bootstrap `config/layers.yaml` from:
      core → user → project → project-local

    Extra layers are inserted into the default overlay stack.
    """
    repo_root = Path(repo_root).resolve()
    project_dir = get_project_config_dir(repo_root, create=False)
    user_dir = get_user_config_dir(create=False)

    core_dir = Path(get_data_path(""))
    core_config_dir = Path(get_data_path("config"))
    bundled_packs_dir = Path(get_data_path("packs"))
    project_local_config_dir = project_dir / "config.local"

    cfg = _load_layers_bootstrap_cfg(
        core_config_dir=core_config_dir,
        user_dir=user_dir,
        project_dir=project_dir,
        project_local_config_dir=project_local_config_dir,
    )
    extra = [e for e in _parse_extra_layers(cfg, repo_root=repo_root) if e.get("enabled", True)]

    # Default stack: user → project (low → high)
    stack: List[LayerSpec] = [
        LayerSpec(id="user", path=user_dir),
        LayerSpec(id="project", path=project_dir),
    ]

    seen = {l.id for l in stack}
    pending = []
    for e in extra:
        if e["id"] in seen:
            raise ValueError(f"Duplicate layer id '{e['id']}' in layers config.")
        pending.append(e)
        seen.add(e["id"])

    # Place extras, allowing references to other extras by doing iterative passes.
    placed_any = True
    while pending and placed_any:
        placed_any = False
        remaining: List[Dict[str, Any]] = []
        for e in pending:
            try:
                _insert_layer(
                    stack,
                    LayerSpec(id=e["id"], path=e["path"]),
                    before=e.get("before"),
                    after=e.get("after"),
                )
                placed_any = True
            except ValueError:
                remaining.append(e)
        pending = remaining

    if pending:
        remaining_ids = {str(e.get("id")) for e in pending}
        all_known = {l.id for l in stack} | remaining_ids
        missing_targets: List[str] = []
        for e in pending:
            target = e.get("before") or e.get("after") or "user"
            if target and str(target) not in all_known:
                missing_targets.append(str(target))
        if missing_targets:
            raise ValueError(
                "Unknown target layer(s) referenced in layers config: "
                + ", ".join(sorted(set(missing_targets)))
                + "."
            )

        unresolved = ", ".join(sorted(remaining_ids))
        raise ValueError(
            f"Could not place layer(s): {unresolved}. Check before/after targets for cycles."
        )

    return LayerStack(
        repo_root=repo_root,
        core_dir=core_dir,
        core_config_dir=core_config_dir,
        bundled_packs_dir=bundled_packs_dir,
        layers=tuple(stack),
        project_local_config_dir=project_local_config_dir,
    )
