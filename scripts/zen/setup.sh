#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EDISON_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ZEN_SERVER_DIR="${EDISON_ROOT}/tools/zen-mcp-server"

echo "🔧 Setting up zen-mcp-server in ${ZEN_SERVER_DIR}"

# Validate zen-mcp-server exists
if [[ ! -d "${ZEN_SERVER_DIR}" ]]; then
  echo "❌ zen-mcp-server not found at ${ZEN_SERVER_DIR}"
  exit 1
fi

# Check for requirements.txt
if [[ ! -f "${ZEN_SERVER_DIR}/requirements.txt" ]]; then
  echo "❌ requirements.txt not found at ${ZEN_SERVER_DIR}/requirements.txt"
  exit 1
fi

# Create virtualenv
echo "📦 Creating virtual environment..."
python3 -m venv "${ZEN_SERVER_DIR}/.venv"

# Activate and install
echo "📥 Installing dependencies..."
source "${ZEN_SERVER_DIR}/.venv/bin/activate"
pip install --upgrade pip
pip install -r "${ZEN_SERVER_DIR}/requirements.txt"

echo "✅ zen-mcp-server setup complete"
echo ""
echo "To use this with Claude Code MCP:"
echo "1. Copy .edison/.mcp.json to your project root or Claude config"
echo "2. Ensure ZEN_WORKING_DIR is set in your environment"
echo "3. Restart Claude Code to pick up the new MCP server"
