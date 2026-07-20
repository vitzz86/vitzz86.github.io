#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON312:-}

if [ -z "$PYTHON" ]; then
  PYTHON=$(command -v python3.12 || command -v python3 || true)
fi

if [ -z "$PYTHON" ] || ! "$PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
  echo "Python 3.10 or newer is required." >&2
  exit 1
fi

"$PYTHON" -m venv --clear "$ROOT/.venv-mcp"
"$ROOT/.venv-mcp/bin/python" -m pip install -r "$ROOT/cockpit_mcp/requirements.txt"
echo "Project Cockpit MCP is ready."
echo "Run: $ROOT/cockpit_mcp/run_mcp.sh"
