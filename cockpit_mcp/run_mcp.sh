#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${COCKPIT_MCP_PYTHON:-"$ROOT/.venv-mcp/bin/python"}

if [ ! -x "$PYTHON" ]; then
  echo "Project Cockpit MCP is not installed. Run: $ROOT/cockpit_mcp/setup.sh" >&2
  exit 1
fi

cd "$ROOT"
exec "$PYTHON" -m cockpit_mcp.server "$@"
