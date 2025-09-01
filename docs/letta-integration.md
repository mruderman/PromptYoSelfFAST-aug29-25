# Letta Integration (HTTP over Tailscale)

This document captures the production integration details, findings, and recommendations for using PromptYoSelf as an MCP server with a self‑hosted Letta server connected over Tailscale.

## Summary

- Letta identifies MCP servers by name (mcp_server_name), not ID.
- ADE wrappers must not require a field like mcp_server_id; use optional mcp_server_name with a sensible default (e.g., "promptyoself").
- Our MCP server now tolerates extra pass‑through args (mcp_server_name/mcp_server_id/request_heartbeat/heartbeat) — forwarded fields won’t break.
- Use HTTP transport to the FastMCP server at `http://<tailscale-ip>:8000/mcp`.

## Managed MCP Server (Recommended)

For production, let Letta manage the MCP server + tools by name. This removes the need to pass any server selector in tool arguments.

Auth (self‑hosted):

```bash
export LETTA_URL="http://100.126.136.121:8283"   # Letta server over Tailscale
export LETTA_TOKEN="$LETTA_SERVER_PASSWORD"      # SECURE=true: use server password as Bearer token
```

Add server and register tools:

```bash
# 1) Add managed MCP server (streamable HTTP)
curl -sS -X PUT "$LETTA_URL/v1/tools/mcp/servers" \
  -H "Authorization: Bearer $LETTA_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "server_name": "promptyoself",
    "type": "streamable_http",
    "server_url": "http://100.76.47.25:8000/mcp"
  }'

# 2) Register all PromptYoSelf tools
for T in promptyoself_inference_diagnostics promptyoself_set_default_agent promptyoself_set_scoped_default_agent promptyoself_get_scoped_default_agent promptyoself_schedule_time promptyoself_schedule_cron promptyoself_schedule_every promptyoself_list promptyoself_cancel promptyoself_execute promptyoself_test promptyoself_agents promptyoself_upload health; do
  curl -sS -X POST "$LETTA_URL/v1/tools/mcp/servers/promptyoself/$T" \
    -H "Authorization: Bearer $LETTA_TOKEN" -H "Content-Type: application/json"; echo
done

# 3) Attach to your agent
AGENT_ID="agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"
curl -sS "$LETTA_URL/v1/tools/mcp/servers/promptyoself/tools" -H "Authorization: Bearer $LETTA_TOKEN" | jq -r '.[].id' | while read -r TID; do
  curl -sS -X PATCH "$LETTA_URL/v1/agents/$AGENT_ID/tools/attach/$TID" \
    -H "Authorization: Bearer $LETTA_TOKEN" -H "Content-Type: application/json"; echo
done
```

Test by messaging the agent (example payload in this repo at `scripts/test_letta_agent_message.sh`).

## Auto‑delivery of scheduled prompts (Executor)

PromptYoSelf includes an execution loop that delivers due prompts. Enable it automatically at server start so agents don’t have to run `promptyoself_execute`:

Options:

- start.sh flags (recommended if you launch MCP via this script):

```bash
./start.sh http --host tailscale --port 8000 --path /mcp \
  --executor --executor-interval 60
```

- Environment variables (if you run without start.sh):

```bash
export PROMPTYOSELF_EXECUTOR_AUTOSTART=true
export PROMPTYOSELF_EXECUTOR_INTERVAL=60
python promptyoself_mcp_server.py --transport http --host 0.0.0.0 --port 8000 --path /mcp
```

This spawns a background process inside the MCP server that runs the execute loop and delivers prompts continuously.

## Server Configuration (Letta)

Update `~/.letta/mcp_config.json` (bound from your host). Example entry:

```json
{
  "mcpServers": {
    "promptyoself": {
      "transport": "http",
      "url": "http://100.76.47.25:8000/mcp"
    }
  }
}
```

- Replace `100.76.47.25` with your PromptYoSelf host’s Tailscale IP.
- Restart Letta to reload MCP configuration.

## ADE Wrapper Recommendations (Optional)

If you still use ADE wrappers, use optional `mcp_server_name` with default "promptyoself". Do not require `mcp_server_id`.

- promptyoself_list:
```json
{
  "type": "object",
  "properties": {
    "mcp_server_name": { "type": "string", "default": "promptyoself" },
    "agent_id": { "type": ["string","null"] },
    "include_cancelled": { "type": "boolean", "default": false }
  },
  "required": []
}
```

- promptyoself_cancel:
```json
{
  "type": "object",
  "properties": {
    "mcp_server_name": { "type": "string", "default": "promptyoself" },
    "schedule_id": { "type": "integer" }
  },
  "required": ["schedule_id"]
}
```

- promptyoself_schedule_time:
```json
{
  "type": "object",
  "properties": {
    "mcp_server_name": { "type": "string", "default": "promptyoself" },
    "agent_id": { "type": ["string","null"] },
    "agentId": { "type": ["string","null"] },
    "prompt": { "type": "string" },
    "time": { "type": "string" },
    "skip_validation": { "type": "boolean", "default": false }
  },
  "required": ["prompt", "time"]
}
```

Apply the same pattern for `promptyoself_schedule_cron`, `promptyoself_schedule_every`, `promptyoself_inference_diagnostics`, `promptyoself_set_default_agent`, `promptyoself_set_scoped_default_agent`, `promptyoself_get_scoped_default_agent` (making `mcp_server_name` optional with default; other required fields tool‑specific).

## MCP Server Tolerance (implemented)

The server accepts and ignores these pass‑through fields on all tools:

- `mcp_server_name`, `mcp_server_id`, `request_heartbeat`, `heartbeat`

This allows uniform forwarding from ADE wrappers without schema friction.

## Testing via cURL

Auth note

For this self‑hosted deployment with SECURE=true, API requests should use the server password as a Bearer token:

```bash
export LETTA_TOKEN="$LETTA_SERVER_PASSWORD"
```

1) List MCP servers

```bash
export LETTA_URL="http://<letta-ip-or-host>:8283"
export LETTA_TOKEN="<your_token>"
curl -sS "$LETTA_URL/v1/tools/mcp/servers" \
  -H "Authorization: Bearer $LETTA_TOKEN"
```

2) List tools for `promptyoself`

```bash
curl -sS "$LETTA_URL/v1/tools/mcp/servers/promptyoself/tools" \
  -H "Authorization: Bearer $LETTA_TOKEN"
```

3) Ask your agent to run a smoke test

```bash
export AGENT_ID="agent-1a4a5989-ab98-478f-9b1f-bbece814ed7a"
curl -sS -X POST "$LETTA_URL/v1/agents/$AGENT_ID/messages" \
  -H "Authorization: Bearer $LETTA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "Please run a quick MCP smoke test for PromptYoSelf. Steps:\n1) Call promptyoself_inference_diagnostics.\n2) Schedule one-time without agent_id (promptyoself_schedule_time) with a future ISO time.\n3) Schedule again with agentId alias.\n4) List schedules (promptyoself_list) and cancel both (promptyoself_cancel).\nUse the MCP server named ‘promptyoself’. Return a short report with IDs, statuses, and any errors."}
        ]
      }
    ]
  }'
```

If your deployment requires a project header, add `-H "X-Project: <project_slug>"`.

## Persistence

- MCP config is persisted at `config/letta/mcp_config.json` and bind‑mounted into the Letta container as `~/.letta/mcp_config.json`. Restart Letta after changes.
- ADE wrapper schema changes should be checked into your ADE configuration so all future tool calls use the relaxed `mcp_server_name` default.
- PromptYoSelf MCP server already tolerates pass‑through fields; no further server configuration is needed.

## Troubleshooting

- HTTP 406 at `/mcp` without `Accept: text/event-stream` is expected; Letta MCP client sets proper headers.
- Connection failures from Letta to providers (e.g., Ollama) won’t affect MCP connectivity, but may surface in logs.
- If tools don’t appear under the `promptyoself` server in Letta, confirm `mcp_config.json` and the FastMCP server is listening on `http://<tailscale-ip>:8000/mcp`.
