from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.data import get_data_path
from edison.core.utils.io import read_yaml
from .metadata import PackMetadata, load_pack_metadata


@dataclass
class ValidationIssue:
    path: str
    code: str
    message: str
    severity: str = "error"


@dataclass
class ValidationResult:
    ok: bool
    issues: List[ValidationIssue]
    normalized: Optional[PackMetadata] = None


def _load_yaml(path: Path) -> Dict[str, Any]:
    return read_yaml(path, default={})


def validate_pack(
    pack_path: Path, schema_path: Optional[Path] = None
) -> ValidationResult:
    issues: List[ValidationIssue] = []
    if not (pack_path / "pack.yml").exists():
        return ValidationResult(
            False, [ValidationIssue("pack.yml", "missing", "pack.yml not found")]
        )

    data = _load_yaml(pack_path / "pack.yml")
    # 1) JSON Schema validation
    if schema_path is None:
        schema_path = get_data_path("schemas") / "pack.schema.json"
    try:
        from jsonschema import Draft202012Validator  # type: ignore
        from edison.core.utils.io import read_json as _io_read_json

        schema = _io_read_json(schema_path)
        Draft202012Validator.check_schema(schema)
        v = Draft202012Validator(schema)
        for err in sorted(v.iter_errors(data), key=lambda e: list(e.path)):
            path = "/".join([str(p) for p in err.path]) or "<root>"
            issues.append(ValidationIssue(path, "schema", err.message))
    except Exception as e:  # pragma: no cover - surfaced as single failure
        issues.append(
            ValidationIssue(
                "<schema>", "schema-load", f"Schema load/validate failed: {e}"
            )
        )

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
                issues.append(
                    ValidationIssue(
                        f"{subdir}/{rel}", "file-missing", f"Referenced file not found: {p}"
                    )
                )

    validators_list = list(data.get("validators") or [])
    _check_files("validators", validators_list)
    _check_files("guidelines", list(data.get("guidelines") or []))
    _check_files("examples", list(data.get("examples") or []))

    # 3) Minimum validator requirements: every pack must provide validators/overlays/global.md
    global_overlay = pack_path / "validators" / "overlays" / "global.md"
    if not global_overlay.exists():
        issues.append(
            ValidationIssue(
                "validators/overlays/global.md",
                "global-validator-missing",
                "Every pack must provide validators/overlays/global.md",
            )
        )

    ok = len([i for i in issues if i.severity == "error"]) == 0
    meta = load_pack_metadata(pack_path) if ok else None
    return ValidationResult(ok, issues, meta)
