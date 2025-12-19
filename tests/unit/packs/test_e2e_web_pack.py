from __future__ import annotations

from pathlib import Path

from edison.core.composition.packs import validate_pack
from edison.core.config import ConfigManager
from edison.core.config.domains.qa import QAConfig
from edison.core.registries.validators import ValidatorRegistry


# Locate repository root
_cur = Path(__file__).resolve()
ROOT = None
for i in range(1, 10):
    if i >= len(_cur.parents):
        break
    cand = _cur.parents[i]
    if (cand / ".git").exists():
        ROOT = cand
        break
assert ROOT is not None, "cannot locate repository root (.git)"

E2E_WEB_PACK = ROOT / "src/edison/data/packs/e2e-web"


def test_e2e_web_pack_validates() -> None:
    res = validate_pack(E2E_WEB_PACK)
    assert res.ok, f"e2e-web pack validation failed: {[i.message for i in res.issues]}"


def test_e2e_web_pack_wires_validator_and_delegation(tmp_path: Path) -> None:
    (tmp_path / ".edison" / "config").mkdir(parents=True)
    (tmp_path / ".edison" / "config" / "packs.yaml").write_text(
        "packs:\n  active:\n    - e2e-web\n",
        encoding="utf-8",
    )

    cfg = ConfigManager(repo_root=tmp_path).load_config(validate=False, include_packs=True)

    # Validator config overlay is present
    validators = ((cfg.get("validation") or {}).get("validators") or {})
    assert "browser-e2e" in validators

    # Delegation config overlay is present
    delegation = (QAConfig(repo_root=tmp_path).delegation_config or {}).get("filePatternRules") or {}
    assert "e2e/**/*" in delegation
    assert "tests/e2e/**/*" in delegation

    # Triggering behavior: UI changes should trigger the browser-e2e validator
    registry = ValidatorRegistry(project_root=tmp_path)
    _always, triggered_blocking, _triggered_optional = registry.get_triggered_validators(
        files=["src/app.tsx"],
        wave="comprehensive",
    )
    assert any(v.id == "browser-e2e" for v in triggered_blocking)

