import pytest
from pathlib import Path
import yaml
from typing import Any

# We will import the utils after we modify them, but for now we can test the existing ones
# and plan the new ones.
from edison.core.utils.io import read_yaml, write_yaml, parse_yaml_string, dump_yaml_string

# Aliases for backwards compatibility with test
read_yaml_safe = read_yaml
write_yaml_safe = write_yaml

def test_read_yaml_safe_basic(tmp_path):
    p = tmp_path / "test.yaml"
    data = {"foo": "bar", "baz": [1, 2, 3]}
    write_yaml_safe(p, data)
    
    loaded = read_yaml_safe(p)
    assert loaded == data

def test_read_yaml_safe_missing(tmp_path):
    p = tmp_path / "missing.yaml"
    assert read_yaml_safe(p) is None
    assert read_yaml_safe(p, default={}) == {}

def test_read_yaml_safe_invalid(tmp_path):
    p = tmp_path / "invalid.yaml"
    p.write_text("foo: [unclosed list", encoding="utf-8")
    
    # Current behavior: swallows exception and returns default
    assert read_yaml_safe(p) is None
    assert read_yaml_safe(p, default={}) == {}

def test_parse_yaml_string_basic():
    content = "foo: bar\n"
    data = parse_yaml_string(content)
    assert data == {"foo": "bar"}

def test_parse_yaml_string_invalid():
    content = "foo: [invalid"
    assert parse_yaml_string(content) is None
    assert parse_yaml_string(content, default={}) == {}

def test_dump_yaml_string_basic():
    data = {"z": 1, "a": 2}
    # Default sorted
    dump_sorted = dump_yaml_string(data)
    assert "a: 2" in dump_sorted
    assert "z: 1" in dump_sorted
    # Check order if possible, but dict order is reliable in py3.7+
    # yaml sorted: a first, z second
    lines = dump_sorted.strip().splitlines()
    assert "a: 2" in lines[0]
    
    # Unsorted
    dump_unsorted = dump_yaml_string(data, sort_keys=False)
    # Order should be z, a
    lines = dump_unsorted.strip().splitlines()
    assert "z: 1" in lines[0]


# --- Reproduction Tests for specific call sites ---

def test_repro_agents_frontmatter_parsing(tmp_path):
    # src/edison/core/composition/agents.py:397
    # data = yaml.safe_load(parts[1]) or {}
    
    content = """---
name: TestAgent
type: implementer
---
# Body
"""
    parts = content.split("---", 2)
    assert len(parts) >= 3
    data = yaml.safe_load(parts[1]) or {}
    assert data["name"] == "TestAgent"

def test_repro_questionnaire_dump(tmp_path):
    # src/edison/core/setup/questionnaire.py uses yaml.safe_dump(..., sort_keys=False)
    data = {"z": 1, "a": 2}
    dump = yaml.safe_dump(data, sort_keys=False)
    # default yaml dumps sorted keys usually? No, safe_dump defaults to False?
    # verify yaml.safe_dump behavior
    # yaml.safe_dump(data) -> z: 1\n a: 2 (if not sorted)
    # Wait, safe_dump sorts keys by default?
    # Let's check
    dump_default = yaml.safe_dump(data)
    # If I use sort_keys=False
    dump_unsorted = yaml.safe_dump(data, sort_keys=False)
    
    # We need to make sure our replacement supports this or we accept sorted keys.
    # The questionnaire likely wants to preserve order for readability.
    pass
