from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..includes import _repo_root
from .loader import PackManifest, load_pack, _load_yaml


def _collect_graph(
    repo_root: Path, selected: List[str]
) -> Tuple[Dict[str, List[str]], Dict[str, PackManifest]]:
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


def compose(
    selected_packs: List[str], *, strategy: str = "latest-wins"
) -> Dict[str, Any]:
    """Compose packs and return a result dict with load order and merged maps.

    Returns keys: packs, loadOrder, dependencies, devDependencies, scripts, conflicts
    """
    repo = _repo_root()
    graph, manifests = _collect_graph(repo, selected_packs)
    load_order = _toposort(graph, selected_packs)

    deps: Dict[str, str] = {}
    dev_deps: Dict[str, str] = {}
    scripts: Dict[str, str] = {}
    conflicts: Dict[str, List[Dict[str, Any]]] = {
        "dependencies": [],
        "devDependencies": [],
        "scripts": [],
    }

    # Determine first occurrence for script names to keep canonical key
    script_owner: Dict[str, str] = {}

    for pack_name in load_order:
        mf = manifests[pack_name]
        # dependencies
        for pkg, ver in mf.dependencies.items():
            if pkg in deps and deps[pkg] != ver:
                chosen = _choose_version(deps[pkg], ver, strategy)
                conflicts["dependencies"].append(
                    {
                        "package": pkg,
                        "versions": [deps[pkg], ver],
                        "resolution": chosen,
                        "packs": [script_owner.get(pkg, "<n/a>"), pack_name],
                    }
                )
                deps[pkg] = chosen if strategy != "first-wins" else deps[pkg]
            else:
                deps[pkg] = ver
                script_owner[pkg] = pack_name

        # devDependencies
        for pkg, ver in mf.dev_dependencies.items():
            if pkg in dev_deps and dev_deps[pkg] != ver:
                chosen = _choose_version(dev_deps[pkg], ver, strategy)
                conflicts["devDependencies"].append(
                    {
                        "package": pkg,
                        "versions": [dev_deps[pkg], ver],
                        "resolution": chosen,
                        "packs": [script_owner.get(pkg, "<n/a>"), pack_name],
                    }
                )
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
                conflicts["scripts"].append(
                    {
                        "script": key,
                        "packs": [script_owner[key], pack_name],
                        "namespaced": ns_key,
                    }
                )

    return {
        "packs": selected_packs,
        "loadOrder": load_order,
        "dependencies": deps,
        "devDependencies": dev_deps,
        "scripts": scripts,
        "conflicts": conflicts,
    }


def compose_from_file(
    config_path: Path, *, strategy: str = "latest-wins"
) -> Dict[str, Any]:
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
