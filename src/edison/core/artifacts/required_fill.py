"""Detect REQUIRED FILL markers in Markdown artifacts.

This module supports a deterministic convention:

  <!-- REQUIRED FILL: <SectionId> -->

When present immediately before a Markdown heading, the heading's section is
considered required and must be filled by a human/LLM. The section is treated as
unfilled when it contains placeholder tokens (config-driven) or is empty after
stripping comments/whitespace.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


@dataclass(frozen=True)
class RequiredFillConfig:
    marker_prefix: str
    marker_suffix: str
    placeholder_token_prefix: str

    def marker_regex(self) -> re.Pattern[str]:
        prefix = re.escape(self.marker_prefix)
        suffix = re.escape(self.marker_suffix)
        return re.compile(rf"{prefix}\s*([A-Za-z0-9_-]+)\s*{suffix}")


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.DOTALL)


def _load_required_fill_cfg(cfg: Mapping[str, Any] | None = None) -> RequiredFillConfig:
    if cfg is None:
        from edison.core.config import ConfigManager

        cfg = ConfigManager().load_config(validate=False)

    artifacts = cfg.get("artifacts") if isinstance(cfg.get("artifacts"), dict) else {}
    required = artifacts.get("requiredFill") if isinstance(artifacts.get("requiredFill"), dict) else {}
    marker = required.get("marker") if isinstance(required.get("marker"), dict) else {}

    marker_prefix = str(marker.get("prefix") or "").strip()
    marker_suffix = str(marker.get("suffix") or "").strip()
    placeholder_token_prefix = str(required.get("placeholderTokenPrefix") or "").strip()

    # Fail-open defaults: core config always provides these, but keep a safe fallback
    # for minimal/standalone environments.
    if not marker_prefix:
        marker_prefix = "<!-- REQUIRED FILL:"
    if not marker_suffix:
        marker_suffix = "-->"
    if not placeholder_token_prefix:
        placeholder_token_prefix = "<<FILL"

    return RequiredFillConfig(
        marker_prefix=marker_prefix,
        marker_suffix=marker_suffix,
        placeholder_token_prefix=placeholder_token_prefix,
    )


def _section_bounds(lines: list[str], start_heading_idx: int) -> tuple[int, int]:
    """Return (start, end) slice bounds for the section body after the heading line."""
    m = _HEADING_RE.match(lines[start_heading_idx])
    if not m:
        return start_heading_idx + 1, start_heading_idx + 1

    level = len(m.group(1))
    start = start_heading_idx + 1
    end = len(lines)

    for i in range(start, len(lines)):
        hm = _HEADING_RE.match(lines[i])
        if not hm:
            continue
        next_level = len(hm.group(1))
        if next_level <= level:
            end = i
            break

    return start, end


def _is_filled(section_text: str, *, placeholder_token_prefix: str) -> bool:
    if not section_text:
        return False

    # Strip HTML comments (template metadata) before checking content.
    cleaned = _HTML_COMMENT_RE.sub("", section_text).strip()
    if not cleaned:
        return False

    if placeholder_token_prefix and placeholder_token_prefix in cleaned:
        return False

    return True


def find_missing_required_sections(markdown: str, *, cfg: Mapping[str, Any] | None = None) -> list[str]:
    """Return required section IDs that are still unfilled.

    Backwards-compatible behavior:
    - If the artifact contains no REQUIRED FILL markers, returns [].
    """
    if not isinstance(markdown, str) or not markdown:
        return []

    required_cfg = _load_required_fill_cfg(cfg)
    marker_re = required_cfg.marker_regex()

    lines = markdown.splitlines()
    missing: list[str] = []
    seen: set[str] = set()

    for idx, line in enumerate(lines):
        m = marker_re.search(line)
        if not m:
            continue
        section_id = str(m.group(1)).strip()
        if not section_id or section_id in seen:
            continue
        seen.add(section_id)

        # Find the heading line for this marker.
        heading_idx = None
        for j in range(idx + 1, len(lines)):
            if _HEADING_RE.match(lines[j]):
                heading_idx = j
                break

        if heading_idx is None:
            missing.append(section_id)
            continue

        start, end = _section_bounds(lines, heading_idx)
        section_body = "\n".join(lines[start:end])
        if not _is_filled(section_body, placeholder_token_prefix=required_cfg.placeholder_token_prefix):
            missing.append(section_id)

    return missing


__all__ = ["find_missing_required_sections", "RequiredFillConfig"]

