#!/usr/bin/env bash
# Edison Hook: session-init
# Type: SessionStart
# Description: Initialize session context

# Consume hook payload from stdin (Claude Code sends JSON); ignore it.
cat >/dev/null 2>&1 || true

command -v edison >/dev/null 2>&1 || exit 0

# Fail-open: hooks must never break the host toolchain.
edison session context 2>/dev/null || true

exit 0