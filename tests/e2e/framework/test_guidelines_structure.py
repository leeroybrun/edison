import pytest
from pathlib import Path
import re

# Corrected path (was parents[6], should be parents[5] based on location)
REPO_ROOT = Path(__file__).resolve().parents[5]
CORE_GUIDELINES = REPO_ROOT / ".edison/core/guidelines"
CORE_EXTENDED = REPO_ROOT / ".edison/core/guides/extended"
CORE_REFERENCE = REPO_ROOT / ".edison/core/guides/reference"

def test_guideline_filename_duplicates():
    """
    FINDING-0XY: Duplicate filenames with different cases (GIT_WORKFLOW.md vs git-workflow.md)
    """
    assert CORE_GUIDELINES.is_dir()
    
    files = [f.name for f in CORE_GUIDELINES.glob("*.md") if f.name != "README.md"]
    lower_map = {}
    duplicates = []
    
    for f in files:
        lower = f.lower()
        if lower in lower_map:
            duplicates.append(f"{f} conflicts with {lower_map[lower]}")
        else:
            lower_map[lower] = f
            
    assert not duplicates, f"Found duplicate guideline filenames (case-insensitive): {duplicates}"

def test_cross_reference_contracts():
    """
    FINDING-0XY: Unclear contract: which is condensed vs extended.
    Need cross-links between short/long versions.
    """
    assert CORE_EXTENDED.is_dir()
    
    guidelines = {f.name: f for f in CORE_GUIDELINES.glob("*.md") if f.name != "README.md"}
    extended_guides = {f.name: f for f in CORE_EXTENDED.glob("*.md")}
    
    # Map extended guides to lowercase for easier matching
    extended_lower = {k.lower(): k for k in extended_guides.keys()}
    
    missing_links = []
    
    for g_name, g_path in guidelines.items():
        # Check if this guideline has an extended version (case-insensitive)
        if g_name.lower() in extended_lower:
            ext_name = extended_lower[g_name.lower()]
            ext_path = extended_guides[ext_name]
            
            # Check 1: Guideline points to Extended
            g_content = g_path.read_text(encoding="utf-8")
            # Expecting roughly: "See extended version in core/guides/extended/..."
            # We'll look for the path or a strong keyword combo
            if f"core/guides/extended/{ext_name}" not in g_content and "extended version" not in g_content.lower():
                missing_links.append(f"Guideline {g_name} missing link to extended version {ext_name}")
                
            # Check 2: Extended points to Guideline
            e_content = ext_path.read_text(encoding="utf-8")
            if f"core/guidelines/{g_name}" not in e_content and "condensed summary" not in e_content.lower():
                missing_links.append(f"Extended guide {ext_name} missing link to guideline {g_name}")
                
    assert not missing_links, f"Missing cross-references:\n" + "\n".join(missing_links)

def test_no_filler_content():
    """
    FINDING-0XY.1.5: Remove filler lines like 'Additional note N: ...'
    """
    patterns = [
        re.compile(r"Additional note \d+:", re.IGNORECASE),
        re.compile(r"Note \d+:", re.IGNORECASE)
    ]
    
    filler_found = []
    
    all_files = list(CORE_GUIDELINES.glob("*.md")) + list(CORE_EXTENDED.glob("*.md"))
    
    for f in all_files:
        content = f.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), 1):
            for p in patterns:
                if p.search(line):
                    filler_found.append(f"{f.name}:{i} - {line.strip()}")
                    
    assert not filler_found, f"Found filler content:\n" + "\n".join(filler_found)

def test_topic_overlap_sanity():
    """
    Ensure specific known duplicates are resolved.
    """
    # Known conflicts from audit
    conflicts = [
        ("GIT_WORKFLOW.md", "git-workflow.md"),
        ("TDD.md", "tdd-workflow.md"),
    ]
    
    files = [f.name for f in CORE_GUIDELINES.glob("*.md")]
    
    for c1, c2 in conflicts:
        if c1 in files and c2 in files:
            pytest.fail(f"Both {c1} and {c2} exist in guidelines. Consolidate them.")