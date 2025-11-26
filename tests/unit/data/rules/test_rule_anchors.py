from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = Path(__file__).with_name("rule_anchor_config.yaml")


def _load_config() -> dict:
    assert CONFIG_PATH.exists(), f"Missing marker config: {CONFIG_PATH}"
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert isinstance(config, dict), "Config must be a mapping"
    return config


def _iter_target_files(config: dict) -> list[Path]:
    target_dirs = config.get("target_dirs") or []
    include_exts = config.get("include_extensions") or []

    assert target_dirs, "Config must provide target_dirs"
    assert include_exts, "Config must provide include_extensions"

    files: list[Path] = []
    for rel_dir in target_dirs:
        target_path = (ROOT / rel_dir).resolve()
        assert target_path.exists(), f"Configured directory missing: {target_path}"
        for path in target_path.rglob("*"):
            if path.is_file() and path.suffix in include_exts:
                files.append(path)
    assert files, "No files discovered for anchor verification"
    return files


def test_rule_files_do_not_contain_html_comment_markers() -> None:
    config = _load_config()
    marker_patterns = config.get("marker_patterns") or []
    assert marker_patterns, "Config must provide marker_patterns"

    regexes = [re.compile(pattern, flags=re.IGNORECASE) for pattern in marker_patterns]

    failures: list[str] = []
    for file_path in _iter_target_files(config):
        content = file_path.read_text(encoding="utf-8")
        for regex in regexes:
            match = regex.search(content)
            if match:
                failures.append(f"{file_path}: {match.group(0)}")

    assert not failures, "HTML comment rule markers must be converted to anchors:\n" + "\n".join(failures)
