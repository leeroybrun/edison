from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Any

from edison.cli import OutputFormatter, get_repo_root
from edison.core.components.service import ComponentKind, ComponentService

DEFAULT_KIND_BY_DOMAIN: dict[str, ComponentKind] = {
    "pack": "pack",
    "validator": "validator",
    "adapter": "adapter",
    "agent": "agent",
}


def resolve_kind_and_id(
    args: argparse.Namespace,
    *,
    kind_or_id: str | None,
    component_id: str | None,
) -> tuple[ComponentKind, str]:
    """Support both:
    - `edison component <cmd> <kind> <id>`
    - `edison pack|validator|adapter|agent <cmd> <id>`
    """
    token1 = str(kind_or_id or "").strip()
    token2 = str(component_id or "").strip()

    if token2:
        kind = token1
        cid = token2
        if kind not in {"pack", "validator", "adapter", "agent"}:
            raise ValueError(f"Unknown component kind: {kind}")
        return kind, cid  # type: ignore[return-value]

    inferred = DEFAULT_KIND_BY_DOMAIN.get(str(getattr(args, "domain", "")).strip())
    if inferred is None:
        raise ValueError("Missing component kind; expected: component <kind> <id>")
    if not token1:
        raise ValueError("Missing component id")
    return inferred, token1


def parse_kv_pairs(pairs: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in pairs or []:
        s = str(raw or "").strip()
        if not s:
            continue
        if "=" not in s:
            raise ValueError(f"Expected KEY=VALUE, got: {s}")
        k, v = s.split("=", 1)
        k = k.strip()
        if not k:
            raise ValueError(f"Expected KEY=VALUE, got: {s}")
        out[k] = v
    return out


def is_interactive(args: argparse.Namespace) -> bool:
    if getattr(args, "non_interactive", False):
        return False
    try:
        import sys

        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except Exception:
        return False


def formatter(args: argparse.Namespace) -> OutputFormatter:
    return OutputFormatter(json_mode=getattr(args, "json", False))


def service(args: argparse.Namespace) -> ComponentService:
    repo_root = get_repo_root(args)
    return ComponentService(repo_root=repo_root)


def status_payload(status_obj: Any) -> dict[str, Any]:
    if hasattr(status_obj, "__dataclass_fields__"):
        return asdict(status_obj)  # type: ignore[arg-type]
    if isinstance(status_obj, dict):
        return dict(status_obj)
    return {"value": status_obj}
