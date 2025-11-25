from functools import lru_cache
import re

_RE_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_RE_MULTI_DASH = re.compile(r"-+")

@lru_cache(maxsize=256)
def slugify(s: str) -> str:
    s = s.strip().lower()
    s = _RE_NON_ALNUM.sub("-", s)
    s = _RE_MULTI_DASH.sub("-", s)
    return s.strip('-')
