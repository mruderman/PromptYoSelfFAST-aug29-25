#!/usr/bin/env bash
set -euo pipefail

# Activate venv if present
if [ -d ".venv" ]; then
  # shellcheck source=/dev/null
  . ".venv/bin/activate"
fi

TRANSPORT="${1:-stdio}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
PATH_ARG="${PATH_ARG:-/mcp}"

case "$TRANSPORT" in
  tailscale)
    # Bind to the Tailscale IPv4 address and use HTTP transport
    if ! command -v tailscale >/dev/null 2>&1; then
      echo "tailscale CLI not found. Install Tailscale or pass an explicit HOST." >&2
      exit 1
    fi
    TS_IP=$(tailscale ip -4 | head -n1 || true)
    if [ -z "${TS_IP:-}" ]; then
      echo "No Tailscale IPv4 address found. Is Tailscale up?" >&2
      exit 1
    fi
    echo "Starting MCP server on Tailscale IP ${TS_IP}:${PORT}${PATH_ARG}"
    exec python promptyoself_mcp_server.py --transport http --host "$TS_IP" --port "$PORT" --path "$PATH_ARG"
    ;;
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