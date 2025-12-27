from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.cli._args import add_standard_flags
from edison.core.composition.registries._types_manager import ComposableTypesManager
from edison.core.composition.registries.generic import GenericRegistry
from edison.core.utils.paths import PathResolver


SUMMARY = "Explain layer resolution for a composable entity"


def register_args(parser: argparse.ArgumentParser) -> None:
    add_standard_flags(parser)
    parser.add_argument("type", help="Composable type (e.g. agents, validators, guidelines)")
    parser.add_argument("name", help="Entity name (e.g. shared/VALIDATION)")
    parser.add_argument(
        "--packs",
        nargs="*",
        help="Override active packs (space-separated or comma-separated list)",
    )


def _parse_packs(raw: Optional[List[str]]) -> Optional[List[str]]:
    if not raw:
        return None
    packs: List[str] = []
    for item in raw:
        for part in str(item).split(","):
            p = part.strip()
            if p:
                packs.append(p)
    return packs or None


def main(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve() if args.repo_root else PathResolver.resolve_project_root()
    packs = _parse_packs(getattr(args, "packs", None))

    # Prefer a configured registry class when available (captures special semantics like guidelines).
    manager = ComposableTypesManager(project_root=repo_root)
    registry = manager.get_registry(args.type)
    if registry is None:
        registry = GenericRegistry(args.type, project_root=repo_root)

    packs = packs or registry.get_active_packs()

    payload: Dict[str, Any] = {
        "type": args.type,
        "name": args.name,
        "packs": list(packs),
        "applied_layers": [],
        "candidates": {
            "core": None,
            "packs": [],
            "user": {"new": None, "overlays": None},
            "project": {"new": None, "overlays": None},
        },
    }

    discovery = registry.discovery
    core = discovery.discover_core()
    existing = set(core.keys())

    if args.name in core:
        payload["candidates"]["core"] = str(core[args.name].path)

    # Pack candidates across all pack roots (bundled → user → project)
    for pack in packs:
        for kind, pack_new, pack_over in discovery.iter_pack_layers(pack, existing):
            if args.name in pack_new:
                payload["candidates"]["packs"].append(
                    {
                        "pack": pack,
                        "pack_root": kind,
                        "kind": "new",
                        "path": str(pack_new[args.name].path),
                    }
                )
            if args.name in pack_over:
                payload["candidates"]["packs"].append(
                    {
                        "pack": pack,
                        "pack_root": kind,
                        "kind": "overlay",
                        "path": str(pack_over[args.name].path),
                    }
                )

    user_new = discovery.discover_user_new(existing)
    if args.name in user_new:
        payload["candidates"]["user"]["new"] = str(user_new[args.name].path)
    existing.update(user_new.keys())
    user_over = discovery.discover_user_overlays(existing)
    if args.name in user_over:
        payload["candidates"]["user"]["overlays"] = str(user_over[args.name].path)

    project_new = discovery.discover_project_new(existing)
    if args.name in project_new:
        payload["candidates"]["project"]["new"] = str(project_new[args.name].path)
    existing.update(project_new.keys())
    project_over = discovery.discover_project_overlays(existing)
    if args.name in project_over:
        payload["candidates"]["project"]["overlays"] = str(project_over[args.name].path)

    # Applied layers: mirror registry semantics but retain pack_root detail.
    applied: List[Dict[str, Any]] = []

    if args.name in core:
        applied.append({"origin": "core", "path": str(core[args.name].path), "kind": "new"})

    core_has_name = args.name in core
    existing_apply = set(core.keys())
    for pack in packs:
        for kind, pack_new, pack_over in discovery.iter_pack_layers(pack, existing_apply):
            if args.name in pack_new and (registry.merge_same_name or not core_has_name):
                applied.append(
                    {
                        "origin": "pack",
                        "pack": pack,
                        "pack_root": kind,
                        "kind": "new",
                        "path": str(pack_new[args.name].path),
                    }
                )
            if args.name in pack_over:
                applied.append(
                    {
                        "origin": "pack",
                        "pack": pack,
                        "pack_root": kind,
                        "kind": "overlay",
                        "path": str(pack_over[args.name].path),
                    }
                )

    if payload["candidates"]["user"]["new"] and (registry.merge_same_name or not core_has_name):
        applied.append({"origin": "user", "kind": "new", "path": payload["candidates"]["user"]["new"]})
    if payload["candidates"]["user"]["overlays"]:
        applied.append({"origin": "user", "kind": "overlay", "path": payload["candidates"]["user"]["overlays"]})
    if payload["candidates"]["project"]["new"] and (registry.merge_same_name or not core_has_name):
        applied.append({"origin": "project", "kind": "new", "path": payload["candidates"]["project"]["new"]})
    if payload["candidates"]["project"]["overlays"]:
        applied.append({"origin": "project", "kind": "overlay", "path": payload["candidates"]["project"]["overlays"]})

    payload["applied_layers"] = applied

    # If nothing was found, exit non-zero.
    if not applied:
        err = {"error": f"{args.type}:{args.name} not found in any layer", **payload}
        if args.json:
            print(json.dumps(err, indent=2, sort_keys=True))
        else:
            print(err["error"])
        return 1

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{args.type}:{args.name}")
        for item in applied:
            if item["origin"] == "pack":
                print(f"- pack[{item['pack_root']}]:{item['pack']} ({item['kind']}): {item['path']}")
            else:
                print(f"- {item['origin']} ({item['kind']}): {item['path']}")

    return 0
