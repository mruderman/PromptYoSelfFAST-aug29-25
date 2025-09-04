#!/usr/bin/env bash
set -euo pipefail

# Activate venv if present
if [ -d ".venv" ]; then
  # shellcheck source=/dev/null
  . ".venv/bin/activate"
fi

# Load .env if present (export all vars during load)
if [ -f .env ]; then
  set -a
  # shellcheck source=/dev/null
  . ./.env
  set +a
fi

# Defaults
TRANSPORT="stdio"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
PATH_ARG="${PATH_ARG:-/mcp}"
DEFAULT_AGENT_ID=""
ENABLE_SINGLE_FALLBACK="false"
ENV_FILE=""
USE_TAILSCALE="false"
ENABLE_EXECUTOR="true"
EXECUTOR_INTERVAL="60"
PERSISTENT_DB_DEFAULT=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    stdio|http|sse|tailscale)
      TRANSPORT="$1"; shift ;;
    --agent-id|-a)
      DEFAULT_AGENT_ID="${2:-}"; shift 2 ;;
    --single|--single-agent-fallback|-s)
      ENABLE_SINGLE_FALLBACK="true"; shift ;;
    --env-file)
      ENV_FILE="${2:-}"; shift 2 ;;
    --host)
      HOST="${2:-}"; shift 2 ;;
    --port)
      PORT="${2:-}"; shift 2 ;;
    --path)
      PATH_ARG="${2:-}"; shift 2 ;;
    --tailscale)
      USE_TAILSCALE="true"; shift ;;
    --executor)
      ENABLE_EXECUTOR="true"; shift ;;
    --no-executor)
      ENABLE_EXECUTOR="false"; shift ;;
    --executor-interval)
      EXECUTOR_INTERVAL="${2:-60}"; shift 2 ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [stdio|http|sse|tailscale] [--agent-id ID] [--single] [--env-file FILE] [--host HOST|tailscale] [--port PORT] [--path PATH] [--tailscale] [--executor|--no-executor] [--executor-interval SECS]" >&2
      exit 2 ;;
  esac
done

# Load additional env file if provided
if [[ -n "$ENV_FILE" ]]; then
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck source=/dev/null
    . "$ENV_FILE"
    set +a
  else
    echo "Warning: --env-file '$ENV_FILE' not found; continuing without it" >&2
  fi
fi

# Apply agent defaults if provided
if [[ -n "$DEFAULT_AGENT_ID" ]]; then
  export LETTA_AGENT_ID="$DEFAULT_AGENT_ID"
  export PROMPTYOSELF_DEFAULT_AGENT_ID="$DEFAULT_AGENT_ID"
fi

# Enable single-agent fallback if requested
if [[ "$ENABLE_SINGLE_FALLBACK" == "true" ]]; then
  export PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=true
fi

# Enable background executor if requested
if [[ "$ENABLE_EXECUTOR" == "true" ]]; then
  export PROMPTYOSELF_EXECUTOR_AUTOSTART=true
  export PROMPTYOSELF_EXECUTOR_INTERVAL="$EXECUTOR_INTERVAL"
fi

# Ensure a persistent database path by default if not provided
if [[ -z "${PROMPTYOSELF_DB:-}" ]]; then
  # Prefer common container/host-mount locations if available
  if [[ -d "/data" && -w "/data" ]]; then
    PERSISTENT_DB_DEFAULT="/data/promptyoself.sqlite3"
  elif [[ -d "/app/promptyoself/instance" || "${TRANSPORT}" == "tailscale" || "${HOST}" == "tailscale" ]]; then
    # Create Docker-style instance dir if running in container-like layout
    mkdir -p /app/promptyoself/instance 2>/dev/null || true
    if [[ -w "/app/promptyoself/instance" ]]; then
      PERSISTENT_DB_DEFAULT="/app/promptyoself/instance/unified.sqlite3"
    fi
  fi
  # Fallback to repo-local ./data directory
  if [[ -z "$PERSISTENT_DB_DEFAULT" ]]; then
    mkdir -p ./data
    PERSISTENT_DB_DEFAULT="$(pwd)/data/promptyoself.sqlite3"
  fi
  export PROMPTYOSELF_DB="$PERSISTENT_DB_DEFAULT"
fi

resolve_tailscale_ip() {
  if [[ -n "${TAILSCALE_IP:-}" ]]; then
    echo "$TAILSCALE_IP"
    return 0
  fi
  if command -v tailscale >/dev/null 2>&1; then
    TS_IP=$(tailscale ip -4 | head -n1 || true)
    if [[ -n "$TS_IP" ]]; then
      echo "$TS_IP"
      return 0
    fi
  fi
  echo ""  # empty means failure
}

# Allow --host tailscale or --tailscale to force binding to TS IP
if [[ "$HOST" == "tailscale" ]]; then
  USE_TAILSCALE="true"
fi

case "$TRANSPORT" in
  tailscale)
    # Bind to the Tailscale IPv4 address and use HTTP transport
    TS_IP=$(resolve_tailscale_ip)
    if [[ -z "$TS_IP" ]]; then
      echo "Could not determine Tailscale IP. Set TAILSCALE_IP or install tailscale CLI." >&2
      exit 1
    fi
    echo "Starting MCP server on Tailscale IP ${TS_IP}:${PORT}${PATH_ARG}"
    exec python promptyoself_mcp_server.py --transport http --host "$TS_IP" --port "$PORT" --path "$PATH_ARG"
    ;;
  http)
    if [[ "$USE_TAILSCALE" == "true" ]]; then
      TS_IP=$(resolve_tailscale_ip)
      if [[ -z "$TS_IP" ]]; then
        echo "Could not determine Tailscale IP. Set TAILSCALE_IP or install tailscale CLI." >&2
        exit 1
      fi
      HOST="$TS_IP"
      echo "Starting MCP server on Tailscale IP http://${HOST}:${PORT}${PATH_ARG}"
    else
      echo "Starting MCP server on http://${HOST}:${PORT}${PATH_ARG}"
    fi
    ARGS=(--transport http --host "$HOST" --port "$PORT" --path "$PATH_ARG")
    if [[ "$ENABLE_EXECUTOR" == "true" ]]; then
      ARGS+=(--autostart-executor --executor-interval "$EXECUTOR_INTERVAL")
    fi
    exec python promptyoself_mcp_server.py "${ARGS[@]}"
    ;;
  sse)
    echo "Starting MCP SSE server on ${HOST}:${PORT}"
    exec python promptyoself_mcp_server.py --transport sse --host "$HOST" --port "$PORT"
    ;;
  stdio|*)
    echo "Starting MCP server on stdio"
    exec python promptyoself_mcp_server.py
    ;;
esac
