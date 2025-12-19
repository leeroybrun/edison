from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("cannot locate repository root (.git)")


def test_composition_default_header_is_deterministic() -> None:
    """Composed files should not churn due to timestamps."""
    root = _repo_root()
    content = (root / "src/edison/data/config/composition.yaml").read_text(encoding="utf-8")
    assert "Generated at:" not in content
    assert "{{timestamp}}" not in content


def test_root_templates_do_not_include_generated_timestamp() -> None:
    """AGENTS.md and CLAUDE.md should not change on every `edison compose all`."""
    root = _repo_root()
    roots_dir = root / "src/edison/data/roots"
    for name in ("AGENTS.md", "CLAUDE.md"):
        text = (roots_dir / name).read_text(encoding="utf-8")
        assert "{{timestamp}}" not in text


def test_typescript_validator_does_not_hardcode_npm_typecheck() -> None:
    root = _repo_root()
    ts_validator = root / "src/edison/data/packs/typescript/validators/typescript.md"
    global_overlay = root / "src/edison/data/packs/typescript/validators/overlays/global.md"
    assert "npm run typecheck" not in ts_validator.read_text(encoding="utf-8")
    assert "npm run typecheck" not in global_overlay.read_text(encoding="utf-8")


def test_validation_guidelines_do_not_reference_bundle_approved_marker() -> None:
    root = _repo_root()
    val = root / "src/edison/data/guidelines/shared/VALIDATION.md"
    assert "bundle-approved" not in val.read_text(encoding="utf-8")


def test_dependency_audit_policy_handles_lockfile_normalization() -> None:
    """Validators must not reject on baseline vulns when versions didn't change."""
    root = _repo_root()
    security = root / "src/edison/data/validators/critical/security.md"
    global_v = root / "src/edison/data/validators/global.md"
    sec_text = security.read_text(encoding="utf-8")
    glob_text = global_v.read_text(encoding="utf-8")

    # Keep this lightweight and intention-revealing (avoid brittle exact wording).
    assert "lockfiles changed" in sec_text
    assert "versions" in sec_text
    assert "lockfiles changed" in glob_text
    assert "versions" in glob_text
