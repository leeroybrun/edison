#!/usr/bin/env bash
# Verify MCP setup using real Edison CLI commands.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Ensure repository sources are used
export PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}"

# Allow overriding the CLI invocation (defaults to repository Edison)
IFS=' ' read -r -a EDISON_CMD <<< "${ZEN_VERIFY_EDISON_CMD:-python3 -m edison}"

# Load YAML-driven MCP configuration into environment variables
eval "$(python3 - <<'PY'
import json, shlex
from edison.data import read_yaml

cfg = read_yaml("config", "mcp.yml") or {}
mcp = (cfg.get("mcp") or {})
servers = mcp.get("servers") or {}

server_id = "edison-zen" if "edison-zen" in servers else (next(iter(servers.keys())) if servers else "unknown")
server = servers.get(server_id, {})

def emit(key: str, value) -> None:
    print(f"{key}={shlex.quote(str(value))}")

emit("ZEN_VERIFY_SERVER_ID", server_id)
emit("ZEN_VERIFY_CONFIG_FILE", mcp.get("config_file", ".mcp.json"))
emit("ZEN_VERIFY_COMMAND_BIN", server.get("command", "edison"))

args = server.get("args") or []
print("ZEN_VERIFY_ARGS=(" + " ".join(shlex.quote(str(a)) for a in args) + ")")
print("ZEN_VERIFY_ARGS_JSON=" + shlex.quote(json.dumps(args)))
print("ZEN_VERIFY_ENV_JSON=" + shlex.quote(json.dumps(server.get("env") or {})))
PY
)"

export ZEN_VERIFY_SERVER_ID ZEN_VERIFY_CONFIG_FILE ZEN_VERIFY_COMMAND_BIN ZEN_VERIFY_ARGS_JSON ZEN_VERIFY_ENV_JSON

TEMP_DIR=""
INIT_DIR=""
EXISTING_DIR=""

cleanup() {
  [[ -d "${TEMP_DIR}" ]] && rm -rf "${TEMP_DIR}"
  [[ -d "${INIT_DIR}" ]] && rm -rf "${INIT_DIR}"
  [[ -d "${EXISTING_DIR}" ]] && rm -rf "${EXISTING_DIR}"
}
trap cleanup EXIT

run_edison() {
  local args=("$@")
  "${EDISON_CMD[@]}" "${args[@]}"
}

verify_json_server_entry() {
  local json_path="$1"
  local project_root="$2"

  python3 - <<'PY' "$json_path" "$project_root"
import json, sys, pathlib, os

json_path = pathlib.Path(sys.argv[1])
project_root = pathlib.Path(sys.argv[2]).resolve()
content = json.loads(json_path.read_text())

server_id = os.environ["ZEN_VERIFY_SERVER_ID"]
expected_args = json.loads(os.environ.get("ZEN_VERIFY_ARGS_JSON", "[]"))
expected_env = json.loads(os.environ.get("ZEN_VERIFY_ENV_JSON", "{}"))

servers = content.get("mcpServers") or {}
if server_id not in servers:
    raise SystemExit(f"Missing server id {server_id} in {json_path}")

cfg = servers[server_id]
if cfg.get("command") != os.environ.get("ZEN_VERIFY_COMMAND_BIN"):
    raise SystemExit(f"Command mismatch: {cfg.get('command')} != {os.environ.get('ZEN_VERIFY_COMMAND_BIN')} in {json_path}")

if list(cfg.get("args") or []) != list(expected_args):
    raise SystemExit(f"Args mismatch in {json_path}: {cfg.get('args')} != {expected_args}")

env = cfg.get("env") or {}
resolved_env = {k: str(v).replace("{PROJECT_ROOT}", str(project_root)) for k, v in expected_env.items()}
for key, value in resolved_env.items():
    if env.get(key) != value:
        raise SystemExit(f"Env mismatch for {key}: {env.get(key)} != {value}")
PY
}

echo "=== Edison MCP Setup Verification ==="

echo
echo "1. Running mcp setup --check..."
if run_edison mcp setup --check >/dev/null 2>&1; then
  echo "   ✅ mcp setup check passed"
else
  echo "   ❌ mcp setup check failed" >&2
  exit 1
fi

echo
echo "2. Testing mcp configure (dry-run)..."
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/zen-verify-XXXXXX")"
DRY_JSON_PATH="${TEMP_DIR}/dry-run.json"

run_edison mcp configure "${TEMP_DIR}" --dry-run >"${DRY_JSON_PATH}"
verify_json_server_entry "${DRY_JSON_PATH}" "${TEMP_DIR}"

if [[ -f "${TEMP_DIR}/${ZEN_VERIFY_CONFIG_FILE}" ]]; then
  echo "   ❌ Dry run should not create ${ZEN_VERIFY_CONFIG_FILE}" >&2
  exit 1
fi
echo "   ✅ dry-run output validated"

echo
echo "3. Testing mcp configure (write)..."
run_edison mcp configure "${TEMP_DIR}" >/dev/null
CONFIG_PATH="${TEMP_DIR}/${ZEN_VERIFY_CONFIG_FILE}"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "   ❌ Expected ${CONFIG_PATH} to be created" >&2
  exit 1
fi
verify_json_server_entry "${CONFIG_PATH}" "${TEMP_DIR}"
echo "   ✅ configuration file created and validated"

echo
echo "4. Testing configure preserves existing servers..."
EXISTING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/zen-existing-XXXXXX")"
EXISTING_PATH="${EXISTING_DIR}/${ZEN_VERIFY_CONFIG_FILE}"
cat >"${EXISTING_PATH}" <<'JSON'
{
  "mcpServers": {
    "other-server": {
      "command": "other",
      "args": [],
      "env": {}
    }
  }
}
JSON

run_edison mcp configure "${EXISTING_DIR}" >/dev/null

python3 - <<'PY' "$EXISTING_PATH"
import json, sys, os
path = sys.argv[1]
data = json.loads(open(path).read())
servers = data.get("mcpServers") or {}
if "other-server" not in servers:
    raise SystemExit("other-server missing after configure")
if os.environ["ZEN_VERIFY_SERVER_ID"] not in servers:
    raise SystemExit("Zen server missing after configure")
PY
echo "   ✅ existing servers preserved"

echo
echo "5. Running edison init integration..."
INIT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/zen-init-XXXXXX")"
run_edison init "${INIT_DIR}" >/dev/null

if [[ ! -d "${INIT_DIR}/.edison" ]]; then
  echo "   ❌ .edison directory missing after init" >&2
  exit 1
fi

INIT_CONFIG_PATH="${INIT_DIR}/${ZEN_VERIFY_CONFIG_FILE}"
if [[ ! -f "${INIT_CONFIG_PATH}" ]]; then
  echo "   ❌ ${ZEN_VERIFY_CONFIG_FILE} missing after init" >&2
  exit 1
fi
verify_json_server_entry "${INIT_CONFIG_PATH}" "${INIT_DIR}"
echo "   ✅ init created MCP config and .edison structure"

echo
echo "=== All MCP verification checks completed ==="
