from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from edison.core.utils.io import ensure_directory


class TeeTextIO:
    def __init__(
        self,
        *,
        primary: TextIO,
        tee_file: TextIO,
        redact_for_file: Callable[[str], str] | None = None,
    ) -> None:
        self._primary = primary
        self._tee_file = tee_file
        self._redact_for_file = redact_for_file

    def write(self, s: str) -> int:
        n = self._primary.write(s)
        try:
            out = self._redact_for_file(s) if self._redact_for_file is not None else s
            self._tee_file.write(out)
        except Exception:
            # Fail-open: never break CLI output because log capture fails.
            pass
        return n

    def flush(self) -> None:
        try:
            self._primary.flush()
        finally:
            try:
                self._tee_file.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        try:
            return self._primary.isatty()
        except Exception:
            return False

    @property
    def encoding(self) -> str:
        return getattr(self._primary, "encoding", "utf-8")


@contextmanager
def capture_stdio(
    *,
    stdout_path: Path | None,
    stderr_path: Path | None,
    redact_for_file: Callable[[str], str] | None = None,
) -> Iterator[None]:
    """Tee stdout/stderr to files while preserving normal terminal output."""
    if stdout_path is None or stderr_path is None:
        yield
        return

    ensure_directory(stdout_path.parent)
    ensure_directory(stderr_path.parent)

    orig_out = sys.stdout
    orig_err = sys.stderr
    out_fh = None
    err_fh = None
    try:
        out_fh = stdout_path.open("a", encoding="utf-8")
        err_fh = stderr_path.open("a", encoding="utf-8")
        sys.stdout = TeeTextIO(primary=orig_out, tee_file=out_fh, redact_for_file=redact_for_file)
        sys.stderr = TeeTextIO(primary=orig_err, tee_file=err_fh, redact_for_file=redact_for_file)
        yield
    finally:
        sys.stdout = orig_out
        sys.stderr = orig_err
        try:
            if out_fh is not None:
                out_fh.flush()
        finally:
            try:
                if out_fh is not None:
                    out_fh.close()
            except Exception:
                pass
        try:
            if err_fh is not None:
                err_fh.flush()
        finally:
            try:
                if err_fh is not None:
                    err_fh.close()
            except Exception:
                pass


__all__ = ["capture_stdio", "TeeTextIO"]
