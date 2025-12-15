"""Central registry for Edison CLI aliases.

This module exists to keep CLI alias behavior unified and easy to extend.

Notes:
- The CLI dispatcher discovers domains from folder names under `edison/cli/`.
- Some folder names end with `_` to avoid Python keyword conflicts (e.g. `import_`).
  For CLI UX, we usually want to expose those without the trailing underscore.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, Iterable, List, Tuple


# Canonical domain (folder) -> extra CLI aliases.
#
# The dispatcher also automatically exposes a trailing-underscore domain (e.g. `import_`)
# as a user-friendly primary name without the underscore (e.g. `import`), while keeping
# the canonical name as an alias.
DOMAIN_ALIASES: Dict[str, List[str]] = {
    # Python keyword avoidance: expose `edison import …` while keeping `edison import_ …`.
    "import_": ["import"],
}


def domain_cli_names(canonical_domain: str) -> Tuple[str, List[str]]:
    """Return (primary, aliases) for an on-disk canonical domain name."""
    primary = canonical_domain
    aliases: List[str] = []

    # Human-friendly primary for keyword-avoiding packages like `import_`.
    if canonical_domain.endswith("_") and len(canonical_domain) > 1:
        primary = canonical_domain[:-1]
        aliases.append(canonical_domain)

    # Explicit aliases (beyond the underscore stripping rule).
    aliases.extend(DOMAIN_ALIASES.get(canonical_domain, []))

    # De-dupe and remove accidental self-aliases.
    seen: set[str] = set()
    out_aliases: List[str] = []
    for a in aliases:
        if not a or a == primary or a in seen:
            continue
        seen.add(a)
        out_aliases.append(a)

    return primary, out_aliases


@lru_cache(maxsize=32)
def build_domain_alias_index(canonical_domains: Tuple[str, ...]) -> Dict[str, str]:
    """Build a lookup map of {cli_token -> canonical_domain}."""
    index: Dict[str, str] = {}
    for canonical in canonical_domains:
        primary, aliases = domain_cli_names(canonical)
        index[canonical] = canonical
        index[primary] = canonical
        for a in aliases:
            index[a] = canonical
    return index


def resolve_canonical_domain(
    token: str,
    *,
    canonical_domains: Iterable[str],
) -> str | None:
    """Resolve a CLI domain token to a canonical on-disk domain folder name."""
    domains_tuple = tuple(sorted(set(str(d) for d in canonical_domains if d)))
    index = build_domain_alias_index(domains_tuple)
    return index.get(token)

