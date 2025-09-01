#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   export LETTA_URL="http://127.0.0.1:8283"
#   export LETTA_TOKEN="<your_token>"
#   export AGENT_ID="agent-..."
#   ./scripts/test_letta_agent_message.sh

# Defaults for self-hosted Letta over Tailscale (VPS)
: "${LETTA_URL:=http://100.126.136.121:8283}"

# Prefer explicit LETTA_TOKEN, otherwise fall back to LETTA_SERVER_PASSWORD if present
if [ -z "${LETTA_TOKEN:-}" ] && [ -n "${LETTA_SERVER_PASSWORD:-}" ]; then
  LETTA_TOKEN="$LETTA_SERVER_PASSWORD"
fi

: "${LETTA_TOKEN:?Set LETTA_TOKEN or export LETTA_SERVER_PASSWORD}"
: "${AGENT_ID:?Set AGENT_ID}"

payload='{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Please run a quick MCP smoke test for PromptYoSelf. Steps:\n1) Call promptyoself_inference_diagnostics.\n2) Schedule one-time without agent_id (promptyoself_schedule_time) with a future ISO time.\n3) Schedule again with agentId alias.\n4) List schedules (promptyoself_list) and cancel both (promptyoself_cancel).\nUse the MCP server named ‘promptyoself’. Return a short report with IDs, statuses, and any errors."
        }
      ]
    }
  ]
}'

curl -sS -X POST "$LETTA_URL/v1/agents/$AGENT_ID/messages" \
  -H "Authorization: Bearer $LETTA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$payload"

echo
