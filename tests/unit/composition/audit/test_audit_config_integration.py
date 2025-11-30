#!/usr/bin/env python3
from __future__ import annotations

"""
Integration tests for guideline duplication configuration.

Requirements (T-027):
- duplication_matrix must read minSimilarity and shingleSize from YAML config
- CLI audit threshold default must come from YAML (no hardcoded numbers)
- NO MOCKS: uses real ConfigManager + filesystem
"""

import argparse
from pathlib import Path

import pytest
import yaml

from tests.helpers.env_setup import setup_project_root
from helpers.io_utils import write_yaml, write_text
from edison.core.composition.audit import GuidelineRecord, duplication_matrix
from edison.cli.qa.audit import register_args


def _write_composition_config(root: Path, *, min_similarity: float, cli_threshold: float, k: int) -> Path:
    """Write composition config with DRY detection parameters."""
    config_dir = root / ".edison" / "config"
    composition_yaml = {
        "composition": {
            "dryDetection": {
                "minShingles": 2,
                "shingleSize": k,
                "minSimilarity": min_similarity,
                "cliThreshold": cli_threshold,
            }
        }
    }
    path = config_dir / "composition.yaml"
    write_yaml(path, composition_yaml)
    return path


def _write_guidelines(root: Path) -> list[GuidelineRecord]:
    """Write sample guideline files for duplication testing."""
    guidelines_dir = root / ".edison" / "guidelines"
    guidelines_dir.mkdir(parents=True, exist_ok=True)

    path_a = guidelines_dir / "dup-a.md"
    path_b = guidelines_dir / "dup-b.md"

    # 10-word samples share 5 of 9 shingles when k=4 (similarity ~0.56)
    write_text(
        path_a,
        "alpha beta gamma delta epsilon zeta eta theta iota kappa\n",
    )
    write_text(
        path_b,
        "alpha beta gamma delta epsilon zeta eta theta lambda mu\n",
    )

    return [
        GuidelineRecord(path=path_a, category="core"),
        GuidelineRecord(path=path_b, category="core"),
    ]


def test_duplication_matrix_uses_config_threshold_and_shingle_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    _write_composition_config(repo_root, min_similarity=0.5, cli_threshold=0.42, k=4)
    records = _write_guidelines(repo_root)

    # Make ConfigManager and path resolution use this isolated repo
    setup_project_root(monkeypatch, repo_root)

    pairs = duplication_matrix(records)

    # With config (k=4, minSimilarity=0.5) we expect one pair; hardcoded defaults (k=12, 0.8) would return none
    assert len(pairs) == 1
    assert 0.5 <= pairs[0]["similarity"] < 0.8


def test_cli_audit_threshold_defaults_to_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    _write_composition_config(repo_root, min_similarity=0.5, cli_threshold=0.37, k=4)
    _write_guidelines(repo_root)

    setup_project_root(monkeypatch, repo_root)

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args([])

    # Threshold should come from composition.yaml, not hardcoded default
    assert args.threshold == pytest.approx(0.37)
