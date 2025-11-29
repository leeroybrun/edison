from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.utils.paths import get_project_config_dir
from edison.core.utils.paths import PathResolver


__all__ = [
    "validate_dimension_weights",
    "process_validator_template",
    "run_validator",
    "_SAFE_INCLUDE_RE",
    "_is_safe_path",
    "_resolve_include_path",
    "_read_text_safe",
]


def validate_dimension_weights(config: Dict[str, Any]) -> None:
    """Validate that validation.dimensions exist and sum to 100."""
    dims = ((config.get("validation") or {}).get("dimensions") or {})
    if not dims:
        raise ValueError(
            "validation.dimensions missing. Define weights in edison.yaml under\n"
            "validation: dimensions: (must sum to 100)."
        )

    total = 0
    for key, value in dims.items():
        try:
            iv = int(value)
        except Exception:
            raise ValueError(
                f"dimension '{key}' must be an integer, got {value!r}. "
                "Define validation.dimensions in your project config "
                "(.edison/config/*.yml)."
            )
        if iv < 0 or iv > 100:
            raise ValueError(
                f"dimension '{key}' must be between 0 and 100, got {iv}. "
                "Adjust the weight in configuration."
            )
        total += iv

    if total != 100:
        raise ValueError(
            f"dimension weights must sum to 100, got {total}. "
            "Update validation.dimensions so the total equals 100."
        )


_SAFE_INCLUDE_RE = re.compile(
    r"\{\{\s*safe_include\(\s*(['\"])"  # opening {{ safe_include(' or "
    r"(?P<path>.+?)\1\s*,\s*fallback\s*=\s*(['\"])"  # path and fallback=
    r"(?P<fallback>.*?)\3\s*\)\s*\}\}"  # closing ) }}
)


def _is_safe_path(rel: str) -> bool:
    if not rel:
        return False
    if rel.startswith(("/", "\\")):
        return False
    if ".." in rel:
        return False
    return True


def _resolve_include_path(rel: str) -> Path | None:
    if not _is_safe_path(rel):
        return None
    try:
        repo_root = PathResolver.resolve_project_root()
        p = (repo_root / rel).resolve()
    except Exception:
        return None
    if p == repo_root or repo_root in p.parents:
        return p if p.is_file() else None
    return None


def _read_text_safe(rel: str) -> str:
    path = _resolve_include_path(rel)
    if not path:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def process_validator_template(template_or_text: str, context: Optional[Dict[str, Any]] = None) -> str:
    given = Path(template_or_text)
    text = given.read_text(encoding="utf-8") if (given.exists() and given.is_file()) else template_or_text

    def _render_safe_include(m: re.Match) -> str:
        rel = m.group("path").strip()
        fallback = m.group("fallback")
        content = _read_text_safe(rel)
        return content if content else fallback

    return _SAFE_INCLUDE_RE.sub(_render_safe_include, text)


def run_validator(validator_markdown_path: str, session_id: str, validator_name: str | None = None) -> str:
    validator_name = validator_name or Path(validator_markdown_path).stem
    repo_root = PathResolver.resolve_project_root()

    # Look for report template in: 1) project validators, 2) bundled templates
    header: str | None = None

    # Priority 1: Project-specific template
    project_template = get_project_config_dir(repo_root, create=False) / "validators" / "_report-template.md"
    if project_template.exists():
        header = project_template.read_text(encoding="utf-8")

    # Priority 2: Bundled template from edison.data
    if header is None:
        try:
            from edison.data import get_data_path
            bundled_template = get_data_path("templates", "_report-template.md")
            if bundled_template.exists():
                header = bundled_template.read_text(encoding="utf-8")
        except Exception:
            pass

    # No fallback: configuration MUST exist
    if header is None:
        raise RuntimeError(
            "Validator report template not found. "
            "Define _report-template.md in either:\n"
            "  1. Project validators: .edison/config/validators/_report-template.md\n"
            "  2. Bundled templates: edison.data/templates/_report-template.md"
        )

    body = process_validator_template(validator_markdown_path, context={
        "session_id": session_id,
        "validator_name": validator_name,
    })

    return f"{header}\n\n---\n\n{body}\n"
