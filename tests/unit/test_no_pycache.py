import sys
from pathlib import Path
import yaml

# Prevent Python from creating new __pycache__ directories during this test run.
sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_pycache_config() -> dict:
    config_path = Path(__file__).parent.parent / "data" / "config" / "no_pycache.yaml"
    with config_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _find_pycache_dirs(repo_root: Path, relative_targets: list[str]) -> list[Path]:
    pycache_dirs: list[Path] = []
    for rel in relative_targets:
        target = (repo_root / rel).resolve()
        if target.exists():
            pycache_dirs.extend([p for p in target.rglob("__pycache__") if p.is_dir()])
    return pycache_dirs


def test_no_pycache_directories_in_src():
    config = _load_pycache_config()
    targets = config.get("targets", [])
    repo_root = REPO_ROOT

    pycache_dirs = _find_pycache_dirs(repo_root, targets)

    assert not pycache_dirs, f"__pycache__ directories present: {pycache_dirs}"
