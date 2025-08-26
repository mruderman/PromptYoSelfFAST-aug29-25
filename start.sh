#!/usr/bin/env bash
set -euo pipefail

# Activate venv if present
if [ -d "venv" ]; then
  # shellcheck source=/dev/null
  . "venv/bin/activate"
fi

TRANSPORT="${1:-stdio}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
PATH_ARG="${PATH_ARG:-/mcp}"

case "$TRANSPORT" in
  http)
    exec python promptyoself_mcp_server.py --transport http --host "$HOST" --port "$PORT" --path "$PATH_ARG"
    ;;
  sse)
    exec python promptyoself_mcp_server.py --transport sse --host "$HOST" --port "$PORT"
    ;;
  stdio|*)
    exec python promptyoself_mcp_server.py
    ;;
esac