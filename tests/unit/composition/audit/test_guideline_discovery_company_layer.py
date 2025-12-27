from __future__ import annotations

from pathlib import Path

from helpers.io_utils import write_yaml


def test_guideline_discovery_includes_company_layer_packs_and_overlays(isolated_project_env: Path) -> None:
    repo = isolated_project_env

    write_yaml(
        repo / ".edison" / "config" / "layers.yaml",
        {
            "layers": {
                "roots": [
                    {
                        "id": "company",
                        "path": ".edison-company",
                        "before": "user",
                    }
                ]
            }
        },
    )

    # Company pack guideline
    pack_guideline = repo / ".edison-company" / "packs" / "alpha" / "guidelines" / "COMPANY.md"
    pack_guideline.parent.mkdir(parents=True, exist_ok=True)
    pack_guideline.write_text("# Company Pack Guideline\n", encoding="utf-8")

    # Company overlay guideline
    company_guideline = repo / ".edison-company" / "guidelines" / "COMPANY_OVERLAY.md"
    company_guideline.parent.mkdir(parents=True, exist_ok=True)
    company_guideline.write_text("# Company Overlay Guideline\n", encoding="utf-8")

    from edison.core.composition.audit import discover_guidelines

    records = discover_guidelines(repo_root=repo)
    paths = {r.path for r in records}

    assert pack_guideline in paths
    assert company_guideline in paths

