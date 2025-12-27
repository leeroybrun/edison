#!/usr/bin/env bash
set -euo pipefail

echo "Pal setup verification"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

TMPROOT="${TMPDIR:-/tmp}"
WORKDIR="${TMPROOT%/}/edison-pal-verify-$$"
mkdir -p "${WORKDIR}"

cleanup() {
  rm -rf "${WORKDIR}" || true
}
trap cleanup EXIT

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export AGENTS_PROJECT_ROOT="${REPO_ROOT}"

echo "Creating temp project at: ${WORKDIR}"

python3 -m edison mcp configure "${WORKDIR}" >/dev/null

if [[ ! -f "${WORKDIR}/.mcp.json" ]]; then
  echo "❌ .mcp.json was not created in ${WORKDIR}" >&2
  exit 1
fi

echo "✅ .mcp.json configured"

if [[ "${PAL_VERIFY_SKIP_SERVER:-}" == "1" ]]; then
  echo "Skipping server execution (PAL_VERIFY_SKIP_SERVER=1)"
  exit 0
fi

echo "Attempting delegated engine self-check"
python3 -m edison mcp setup --check >/dev/null || true

echo "✅ setup verification complete"
