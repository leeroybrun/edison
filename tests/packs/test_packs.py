from __future__ import annotations

import textwrap
from pathlib import Path

import sys

_cur = Path(__file__).resolve()
ROOT = None
for i in range(1, 10):
    if i >= len(_cur.parents):
        break
    cand = _cur.parents[i]
    if (cand / '.git').exists():
        ROOT = cand
        break
assert ROOT is not None, 'cannot locate repository root (.git)'

from edison.core.packs import (
    validate_pack,
    discover_packs,
    resolve_dependencies,
    PackInfo,
    load_active_packs,
    load_pack,
)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_sample_typescript_pack_validates_ok():
    pack_dir = Path('.edison/packs/typescript').resolve()
    assert pack_dir.exists(), "sample typescript pack should exist"
    res = validate_pack(pack_dir)
    assert res.ok, f"validation issues: {[i.message for i in res.issues]}"


def test_validate_pack_missing_fields(tmp_path: Path):
    p = tmp_path / '.edison/packs/minimal'
    write(p / 'pack.yml', textwrap.dedent('''
        name: minimal
        description: missing version
    '''))
    res = validate_pack(p)
    assert not res.ok
    assert any(i.code == 'schema' for i in res.issues)


def test_validate_pack_missing_file_refs(tmp_path: Path):
    p = tmp_path / '.edison/packs/broken'
    write(p / 'pack.yml', textwrap.dedent('''
        name: broken
        version: 1.0.0
        description: references missing files
        triggers:
          filePatterns: ["**/*.ts"]
        validators: [nope.md]
        guidelines: [missing.md]
        examples: [absent.ts]
    '''))
    res = validate_pack(p)
    assert not res.ok
    codes = {i.code for i in res.issues}
    assert 'file-missing' in codes


def test_validate_pack_requires_triggers_file_patterns(tmp_path: Path):
    """Pack manifests must declare triggers.filePatterns (no legacy list-only form)."""
    p = tmp_path / '.edison/packs/missing_triggers'
    write(
        p / 'pack.yml',
        textwrap.dedent(
            '''
            name: missing-triggers
            version: 1.0.0
            description: pack without triggers
            '''
        ),
    )
    res = validate_pack(p)
    assert not res.ok
    codes = {i.code for i in res.issues}
    assert 'schema' in codes, "Expected schema validation error for missing triggers.filePatterns"


def test_validate_pack_requires_codex_context_validator(tmp_path: Path):
    """Every pack must provide at least a codex-context.md validator."""
    p = tmp_path / '.edison/packs/no_codex'
    write(
        p / 'pack.yml',
        textwrap.dedent(
            '''
            name: no-codex
            version: 1.0.0
            description: pack without codex validator
            triggers:
              filePatterns: ["**/*.ts"]
            validators: []
            '''
        ),
    )
    # No validators/codex-context.md file on disk
    res = validate_pack(p)
    assert not res.ok
    codes = {i.code for i in res.issues}
    assert 'codex-validator-missing' in codes


def test_discover_packs_finds_typescript():
    found = discover_packs()
    names = [p.name for p in found]
    assert 'typescript' in names


def test_dependency_resolution_and_cycles(tmp_path: Path):
    # Build a fake repo root with three packs and a cycle
    base = tmp_path / '.edison/packs'
    # Helper to write a minimal, schema-compliant pack with codex-context validator
    def write_pack(name: str, dependencies: list[str]) -> None:
        write(
            base / f"{name}/pack.yml",
            textwrap.dedent(
                f"""
                name: {name}
                version: 1.0.0
                description: {name}
                triggers:
                  filePatterns: ["**/*.ts"]
                dependencies: {dependencies}
                validators: ["codex-context.md"]
                """
            ),
        )
        write(base / f"{name}/validators/codex-context.md", "# validator")

    # a -> b -> c
    write_pack("a", ["b"])
    write_pack("b", ["c"])
    write_pack("c", [])
    # d <-> e (cycle)
    write_pack("d", ["e"])
    write_pack("e", ["d"])

    # Build PackInfo map
    def meta(path: Path):
        res = validate_pack(path)
        assert res.ok, f"pack at {path} should validate in dependency resolution test"
        return res.normalized  # type: ignore[return-value]

    packs = {
        'a': PackInfo('a', base / 'a', meta(base / 'a')),  # type: ignore[arg-type]
        'b': PackInfo('b', base / 'b', meta(base / 'b')),  # type: ignore[arg-type]
        'c': PackInfo('c', base / 'c', meta(base / 'c')),  # type: ignore[arg-type]
        'd': PackInfo('d', base / 'd', meta(base / 'd')),  # type: ignore[arg-type]
        'e': PackInfo('e', base / 'e', meta(base / 'e')),  # type: ignore[arg-type]
    }
    dep = resolve_dependencies(packs)
    # a,b,c should be in order with c before b before a
    order = dep.ordered
    assert order.index('c') < order.index('b') < order.index('a')
    # cycles reported for d/e
    assert dep.cycles, 'expected cycle list'


def test_load_active_packs_from_config_dict():
    cfg = { 'packs': { 'active': ['typescript', 'react'] } }
    active = load_active_packs(cfg)
    assert active == ['typescript', 'react']


def test_load_pack_uses_yaml_dependencies_only(tmp_path: Path):
    """Pack loader should read dependencies from pack-dependencies.yaml (YAML single source of truth)."""
    repo = tmp_path
    base = repo / ".edison/packs/demo"
    write(
        base / "defaults.yaml",
        textwrap.dedent(
            """
            scripts:
              demo: "echo demo"
            """
        ),
    )
    write(
        base / "pack-dependencies.yaml",
        textwrap.dedent(
            """
            requiredPacks: [typescript]
            dependencies:
              demo-lib: "^1.0.0"
            devDependencies:
              demo-dev-lib: "^2.0.0"
            """
        ),
    )

    mf = load_pack(repo, "demo")
    assert mf.dependencies == {"demo-lib": "^1.0.0"}
    assert mf.dev_dependencies == {"demo-dev-lib": "^2.0.0"}
    assert mf.required_packs == ["typescript"]
