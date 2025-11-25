from __future__ import annotations

"""Edison Pack Loader and Composer.

Responsibilities:
- Load pack manifests from `.edison/packs/<name>/` (defaults.yaml, pack-dependencies.yaml).
- Resolve dependency order with a toposort based on `requiredPacks`.
- Compose dependencies, devDependencies, and scripts with conflict detection and
  strategies: `latest-wins` (default), `first-wins`, and `strict`.
- Namespace conflicting scripts as `<pack>:<script>` while keeping the first
  occurrence under its original name.

This module is intentionally dependency-lite and self-contained so scripts can
import it directly without extra setup.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json
import os

from edison.core.utils.git import get_repo_root
from .io_utils import read_json_safe as io_read_json_safe

try:
    import yaml  # type: ignore
except Exception as err:  # pragma: no cover
    raise RuntimeError("PyYAML is required for pack loading: pip install pyyaml") from err


@dataclass
class PackManifest:
    name: str
    path: Path
    dependencies: Dict[str, str]
    dev_dependencies: Dict[str, str]
    scripts: Dict[str, str]
    required_packs: List[str]


def _repo_root() -> Path:
    """Resolve repository root via shared git utility."""
    return get_repo_root()


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return io_read_json_safe(path) or {}


def _pack_dir(repo_root: Path, name: str) -> Path:
    return repo_root / ".edison" / "packs" / name


def load_pack(repo_root: Path, name: str) -> PackManifest:
    pdir = _pack_dir(repo_root, name)
    if not pdir.exists():
        raise FileNotFoundError(f"Pack '{name}' not found at {pdir}")

    defaults = _load_yaml(pdir / "defaults.yaml")
    deps_yaml = _load_yaml(pdir / "pack-dependencies.yaml")
    deps = deps_yaml.get("dependencies") or {}
    dev_deps = deps_yaml.get("devDependencies") or {}
    req = deps_yaml.get("requiredPacks") or []

    scripts = defaults.get("scripts", {}) or {}
    return PackManifest(
        name=name,
        path=pdir,
        dependencies=dict(deps),
        dev_dependencies=dict(dev_deps),
        scripts=scripts,
        required_packs=list(req or []),
    )


def _collect_graph(repo_root: Path, selected: List[str]) -> Tuple[Dict[str, List[str]], Dict[str, PackManifest]]:
    manifests: Dict[str, PackManifest] = {}
    graph: Dict[str, List[str]] = {}

    def visit(name: str) -> None:
        if name in manifests:
            return
        mf = load_pack(repo_root, name)
        manifests[name] = mf
        graph[name] = list(mf.required_packs)
        for dep in mf.required_packs:
            visit(dep)

    for n in selected:
        visit(n)
    return graph, manifests


def _toposort(graph: Dict[str, List[str]], selected_order: List[str]) -> List[str]:
    """Topologically sort packs so that dependencies appear before dependents.

    ``graph`` is given as ``node -> [required_packs]``. Convert to adjacency
    of ``dependency -> [dependents]`` for Kahn's algorithm so in-degree equals
    number of prerequisites.
    """
    # Build adjacency: dep -> [dependents]
    adj: Dict[str, List[str]] = {n: [] for n in graph}
    indeg: Dict[str, int] = {n: 0 for n in graph}
    for node, deps in graph.items():
        for dep in deps:
            adj.setdefault(dep, []).append(node)
            indeg[node] = indeg.get(node, 0) + 1
            adj.setdefault(node, adj.get(node, []))
            indeg.setdefault(dep, indeg.get(dep, 0))

    preferred = {name: i for i, name in enumerate(selected_order)}
    ready = [n for n, d in indeg.items() if d == 0]
    order: List[str] = []
    while ready:
        # Tie-break using original selection order
        ready.sort(key=lambda x: preferred.get(x, 10_000))
        n = ready.pop(0)
        order.append(n)
        for m in adj.get(n, []):
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
    if len(order) != len(indeg):
        raise ValueError("Cycle detected in pack dependency graph")
    return order


def _parse_semver(v: str) -> Tuple[int, int, int]:
    # Very small parser: strips ^/~ and pre-release data; non-numeric → zeros
    s = v.strip()
    if s and s[0] in "^~":
        s = s[1:]
    core = s.split("-")[0]
    parts = (core.split(".") + ["0", "0", "0"])[:3]
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        return (0, 0, 0)


def _choose_version(a: str, b: str, strategy: str) -> str:
    if strategy == "first-wins":
        return a
    if strategy == "strict":
        if a != b:
            raise ValueError(f"Dependency conflict (strict): {a} vs {b}")
        return a
    # latest-wins: prefer numerically larger semver, fall back to b (later)
    return a if _parse_semver(a) >= _parse_semver(b) else b


def compose(selected_packs: List[str], *, strategy: str = "latest-wins") -> Dict[str, Any]:
    """Compose packs and return a result dict with load order and merged maps.

    Returns keys: packs, loadOrder, dependencies, devDependencies, scripts, conflicts
    """
    repo = _repo_root()
    graph, manifests = _collect_graph(repo, selected_packs)
    load_order = _toposort(graph, selected_packs)

    deps: Dict[str, str] = {}
    dev_deps: Dict[str, str] = {}
    scripts: Dict[str, str] = {}
    conflicts: Dict[str, List[Dict[str, Any]]] = {"dependencies": [], "devDependencies": [], "scripts": []}

    # Determine first occurrence for script names to keep canonical key
    script_owner: Dict[str, str] = {}

    for pack_name in load_order:
        mf = manifests[pack_name]
        # dependencies
        for pkg, ver in mf.dependencies.items():
            if pkg in deps and deps[pkg] != ver:
                chosen = _choose_version(deps[pkg], ver, strategy)
                conflicts["dependencies"].append({
                    "package": pkg,
                    "versions": [deps[pkg], ver],
                    "resolution": chosen,
                    "packs": [script_owner.get(pkg, "<n/a>"), pack_name],
                })
                deps[pkg] = chosen if strategy != "first-wins" else deps[pkg]
            else:
                deps[pkg] = ver
                script_owner[pkg] = pack_name

        # devDependencies
        for pkg, ver in mf.dev_dependencies.items():
            if pkg in dev_deps and dev_deps[pkg] != ver:
                chosen = _choose_version(dev_deps[pkg], ver, strategy)
                conflicts["devDependencies"].append({
                    "package": pkg,
                    "versions": [dev_deps[pkg], ver],
                    "resolution": chosen,
                    "packs": [script_owner.get(pkg, "<n/a>"), pack_name],
                })
                dev_deps[pkg] = chosen if strategy != "first-wins" else dev_deps[pkg]
            else:
                dev_deps[pkg] = ver
                script_owner[pkg] = pack_name

        # scripts
        for key, cmd in mf.scripts.items():
            if key not in scripts:
                scripts[key] = cmd
                script_owner[key] = pack_name
            else:
                if scripts[key] == cmd:
                    continue  # identical → skip
                # namespace conflict under <pack>:<key>
                ns_key = f"{pack_name}:{key}"
                scripts[ns_key] = cmd
                conflicts["scripts"].append({
                    "script": key,
                    "packs": [script_owner[key], pack_name],
                    "namespaced": ns_key,
                })

    return {
        "packs": selected_packs,
        "loadOrder": load_order,
        "dependencies": deps,
        "devDependencies": dev_deps,
        "scripts": scripts,
        "conflicts": conflicts,
    }


def compose_from_file(config_path: Path, *, strategy: str = "latest-wins") -> Dict[str, Any]:
    cfg = _load_yaml(config_path)
    packs = cfg.get("packs") or []
    if not isinstance(packs, list) or not packs:
        raise ValueError("edison.yaml contains no packs; nothing to compose")
    # Normalize string-only list; ignore object-form for now (future extension)
    names = []
    for item in packs:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and "name" in item:
            names.append(str(item["name"]))
        else:
            raise ValueError(f"Unsupported packs entry: {item}")
    return compose(names, strategy=strategy)


# ------------------------------------------------------------
# Pack Engine v2 (pack.yml based) — non‑breaking alongside legacy helpers
# ------------------------------------------------------------
from dataclasses import dataclass as _dataclass
from typing import Optional as _Optional, Set as _Set, NamedTuple as _NamedTuple


@_dataclass
class PackMetadata:
    name: str
    version: str
    description: str
    category: _Optional[str] = None
    tags: _Optional[List[str]] = None
    triggers: _Optional[List[str]] = None
    dependencies: _Optional[List[str]] = None
    validators: _Optional[List[str]] = None
    guidelines: _Optional[List[str]] = None
    examples: _Optional[List[str]] = None


@_dataclass
class ValidationIssue:
    path: str
    code: str
    message: str
    severity: str = "error"


@_dataclass
class ValidationResult:
    ok: bool
    issues: List[ValidationIssue]
    normalized: _Optional[PackMetadata] = None


@_dataclass
class PackInfo:
    name: str
    path: Path
    meta: PackMetadata


class DependencyResult(_NamedTuple):
    ordered: List[str]
    cycles: List[List[str]]
    unknown: List[str]


def _repo_root_v2() -> Path:
    return _repo_root()


def _packs_dir_from_cfg(cfg: Dict[str, Any]) -> Path:
    base = cfg.get("packs", {}) if isinstance(cfg, dict) else {}
    directory = base.get("directory") or ".edison/packs"
    return _repo_root_v2() / str(directory)


def load_active_packs(config: Dict[str, Any]) -> List[str]:
    packs = (config.get("packs") or {}).get("active") or []
    return [str(x) for x in packs if isinstance(x, str)]


def load_pack_metadata(pack_path: Path) -> PackMetadata:
    yml = _load_yaml(pack_path / "pack.yml")
    raw_triggers = yml.get("triggers") or {}
    trigger_patterns: List[str] = []
    if isinstance(raw_triggers, dict):
        trigger_patterns = list(raw_triggers.get("filePatterns") or [])
    elif isinstance(raw_triggers, list):
        # Legacy shape (Phase 2) – treat list as file patterns for backward compatibility
        trigger_patterns = list(raw_triggers or [])

    return PackMetadata(
        name=str(yml.get("name", "")),
        version=str(yml.get("version", "")),
        description=str(yml.get("description", "")),
        category=yml.get("category"),
        tags=list(yml.get("tags") or []),
        triggers=trigger_patterns,
        dependencies=list(yml.get("dependencies") or []),
        validators=list(yml.get("validators") or []),
        guidelines=list(yml.get("guidelines") or []),
        examples=list(yml.get("examples") or []),
    )


def validate_pack(pack_path: Path, schema_path: _Optional[Path] = None) -> ValidationResult:
    issues: List[ValidationIssue] = []
    if not (pack_path / "pack.yml").exists():
        return ValidationResult(False, [ValidationIssue("pack.yml", "missing", "pack.yml not found")])

    data = _load_yaml(pack_path / "pack.yml")
    # 1) JSON Schema validation
    if schema_path is None:
        schema_path = _repo_root_v2() / ".edison" / "core" / "schemas" / "pack.schema.json"
    try:
        from jsonschema import Draft202012Validator  # type: ignore
        from .io_utils import read_json_safe as _io_read_json_safe  # type: ignore
        schema = _io_read_json_safe(schema_path)
        Draft202012Validator.check_schema(schema)
        v = Draft202012Validator(schema)
        for err in sorted(v.iter_errors(data), key=lambda e: list(e.path)):
            path = "/".join([str(p) for p in err.path]) or "<root>"
            issues.append(ValidationIssue(path, "schema", err.message))
    except Exception as e:  # pragma: no cover - surfaced as single failure
        issues.append(ValidationIssue("<schema>", "schema-load", f"Schema load/validate failed: {e}"))

    # 1b) Explicit invariants for core fields so packs fail fast even if
    # JSON Schema draft semantics change.
    for key in ("name", "version", "description"):
        val = str(data.get(key, "") or "").strip()
        if not val:
            issues.append(
                ValidationIssue(
                    key,
                    "schema",
                    f"Missing required field: {key}",
                )
            )

    triggers_val = data.get("triggers")
    patterns_val = None
    if isinstance(triggers_val, dict):
        patterns_val = triggers_val.get("filePatterns")
    elif isinstance(triggers_val, list):
        # Legacy shape – treat list as filePatterns
        patterns_val = triggers_val
    if not (isinstance(patterns_val, list) and patterns_val):
        issues.append(
            ValidationIssue(
                "triggers/filePatterns",
                "schema",
                "triggers.filePatterns must be a non-empty list of glob patterns",
            )
        )

    # 2) File existence checks
    def _check_files(subdir: str, files: List[str]) -> None:
        for rel in files or []:
            p = pack_path / subdir / rel
            if not p.exists():
                issues.append(ValidationIssue(f"{subdir}/{rel}", "file-missing", f"Referenced file not found: {p}"))

    validators_list = list(data.get("validators") or [])
    _check_files("validators", validators_list)
    _check_files("guidelines", list(data.get("guidelines") or []))
    _check_files("examples", list(data.get("examples") or []))

    # 3) Minimum validator requirements: every pack must provide codex-context.md
    codex_required = "codex-context.md"
    if codex_required not in validators_list:
        issues.append(
            ValidationIssue(
                f"validators/{codex_required}",
                "codex-validator-missing",
                "Every pack must declare codex-context.md in its validators list",
            )
        )

    ok = len([i for i in issues if i.severity == "error"]) == 0
    meta = load_pack_metadata(pack_path) if ok else None
    return ValidationResult(ok, issues, meta)


def discover_packs(root: _Optional[Path] = None) -> List[PackInfo]:
    root = root or _repo_root_v2()
    base = root / ".edison" / "packs"
    results: List[PackInfo] = []
    if not base.exists():
        return results
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("_"):
            continue  # not a real pack
        if not (child / "pack.yml").exists():
            continue
        v = validate_pack(child)
        if v.ok and v.normalized:
            results.append(PackInfo(v.normalized.name, child, v.normalized))
    return results


def resolve_dependencies(packs: Dict[str, PackInfo]) -> DependencyResult:
    # Build graph of name -> required list
    graph: Dict[str, List[str]] = {n: list((p.meta.dependencies or [])) for n, p in packs.items()}
    # Track unknown deps
    unknown: List[str] = []
    for name, deps in graph.items():
        for d in deps:
            if d not in packs:
                unknown.append(f"{name}:{d}")

    # Kahn's algorithm
    indeg: Dict[str, int] = {n: 0 for n in graph}
    for n, deps in graph.items():
        for d in deps:
            if d in indeg:
                indeg[n] += 1

    ready = [n for n, d in indeg.items() if d == 0]
    order: List[str] = []
    adj: Dict[str, List[str]] = {n: [] for n in graph}
    for n, deps in graph.items():
        for d in deps:
            adj.setdefault(d, []).append(n)

    while ready:
        ready.sort()
        n = ready.pop(0)
        order.append(n)
        for m in adj.get(n, []):
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)

    cycles: List[List[str]] = []
    if len(order) != len(graph):
        # Find remaining nodes in cycle
        remaining = [n for n, d in indeg.items() if d > 0]
        cycles.append(remaining)

    return DependencyResult(order, cycles, unknown)


__all__ = [
    "compose",
    "compose_from_file",
    "load_pack",
    "PackManifest",
    # v2
    "PackMetadata",
    "ValidationIssue",
    "ValidationResult",
    "PackInfo",
    "DependencyResult",
    "discover_packs",
    "validate_pack",
    "load_pack_metadata",
    "resolve_dependencies",
    "load_active_packs",
]
