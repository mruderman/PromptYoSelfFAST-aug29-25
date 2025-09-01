#!/usr/bin/env python3
"""
Setup Letta MCP server, register PromptYoSelf tools, attach to an agent, and optionally
send the agent a message with test instructions.

Requirements:
  pip install letta-client python-dotenv

Environment (or CLI args):
  LETTA_BASE_URL           (optional) e.g. http://127.0.0.1:8283
  LETTA_API_KEY            (preferred) or LETTA_SERVER_PASSWORD
  LETTA_PROJECT            (optional) project slug for cloud

CLI args:
  --server-name NAME       Unique MCP server name to create/update (default: promptyoself)
  --agent-id ID            Target Letta agent to attach tools to
  --send-message           Send a test instruction message to the agent
  --stdio-cmd CMD          Command to launch MCP server (default: python)
  --stdio-args ...         Arguments for MCP server (default: promptyoself_mcp_server.py)

Typical local use (stdio):
  python scripts/setup_letta_mcp.py --server-name promptyoself --agent-id agt_... \
    --stdio-cmd python --stdio-args promptyoself_mcp_server.py

This will register a stdio MCP server in Letta that launches the FastMCP server in stdio mode.
"""

from __future__ import annotations

import os
import sys
import argparse
from typing import List

try:
    from letta_client import Letta, StdioServerConfig
except Exception as e:
    print("letta-client is required. Install with: pip install letta-client", file=sys.stderr)
    raise


def get_client() -> Letta:
    base_url = os.getenv("LETTA_BASE_URL")
    token = os.getenv("LETTA_API_KEY")
    server_password = os.getenv("LETTA_SERVER_PASSWORD")
    project = os.getenv("LETTA_PROJECT")

    # The Python SDK typically takes token; for local password-based auth, rely on base_url+password
    kwargs = {}
    if base_url:
        kwargs["base_url"] = base_url
    if token:
        kwargs["token"] = token
    if project:
        kwargs["project"] = project

    if not token and not server_password and not base_url:
        print("Warning: No LETTA_API_KEY or LETTA_SERVER_PASSWORD/LETTA_BASE_URL provided. Client may fail.", file=sys.stderr)
    return Letta(**kwargs)


def ensure_mcp_server(client: Letta, server_name: str, cmd: str, args: List[str]) -> None:
    cfg = StdioServerConfig(server_name=server_name, command=cmd, args=args)
    # Add or update server
    try:
        client.tools.add_mcp_server(request=cfg)
        print(f"Added MCP server '{server_name}'")
    except Exception as e:
        # Try update if exists
        try:
            from letta_client import UpdateStdioMcpServer  # type: ignore
            client.tools.update_mcp_server(mcp_server_name=server_name, request=UpdateStdioMcpServer())
            print(f"Updated MCP server '{server_name}'")
        except Exception:
            print(f"Warning: could not add/update server '{server_name}': {e}")

    # Test server connectivity (lists tools)
    try:
        res = client.tools.test_mcp_server(request=cfg)
        print(f"Tested MCP server '{server_name}' OK")
    except Exception as e:
        print(f"Warning: test_mcp_server failed for '{server_name}': {e}")


def add_tools_for_server(client: Letta, server_name: str, tools: List[str]) -> None:
    for tool in tools:
        try:
            client.tools.add_mcp_tool(mcp_server_name=server_name, mcp_tool_name=tool)
            print(f"Registered tool '{tool}' on server '{server_name}'")
        except Exception as e:
            print(f"Warning: add_mcp_tool failed for {tool}: {e}")


def list_server_tool_ids(client: Letta, server_name: str) -> dict[str, str]:
    # Return name->id mapping
    mapping: dict[str, str] = {}
    try:
        tools = client.tools.list_mcp_tools_by_server(mcp_server_name=server_name)
        for t in tools or []:
            try:
                name = getattr(t, "name", None) or t.get("name")  # type: ignore
                tid = getattr(t, "id", None) or t.get("id")  # type: ignore
                if name and tid:
                    mapping[str(name)] = str(tid)
            except Exception:
                continue
    except Exception as e:
        print(f"Warning: could not list tools for server '{server_name}': {e}")
    return mapping


def attach_tools_to_agent(client: Letta, agent_id: str, tool_ids: List[str]) -> None:
    for tid in tool_ids:
        try:
            client.agents.tools.attach(agent_id=agent_id, tool_id=tid)
            print(f"Attached tool_id '{tid}' to agent '{agent_id}'")
        except Exception as e:
            print(f"Warning: attach tool_id {tid} failed: {e}")


def send_test_message(client: Letta, agent_id: str, server_name: str) -> None:
    from letta_client import MessageCreate, TextContent
    steps = (
        f"1) Call promptyoself_inference_diagnostics with mcp_server_name='{server_name}'.\n"
        f"2) Schedule one-time without agent_id: promptyoself_schedule_time (time in future).\n"
        f"3) Schedule one-time with agentId alias.\n"
        f"4) List schedules and cancel both.\n"
        f"Note: Include mcp_server_name in tool args if required by the wrapper."
    )
    msg = (
        "Please run a quick MCP smoke test for PromptYoSelf.\n" + steps +
        "\nReturn a short report with IDs, statuses, and any errors."
    )
    try:
        client.agents.messages.create(
            agent_id=agent_id,
            messages=[MessageCreate(role="user", content=[TextContent(text=msg)])],
        )
        print(f"Sent test instructions to agent {agent_id}")
    except Exception as e:
        print(f"Warning: failed to send message to agent {agent_id}: {e}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Configure Letta MCP for PromptYoSelf and attach tools to an agent")
    ap.add_argument("--server-name", default="promptyoself")
    ap.add_argument("--agent-id", required=True)
    ap.add_argument("--send-message", action="store_true")
    ap.add_argument("--stdio-cmd", default="python")
    ap.add_argument("--stdio-args", nargs=argparse.REMAINDER, default=["promptyoself_mcp_server.py"])  # stdio
    args = ap.parse_args()

    client = get_client()

    ensure_mcp_server(client, args.server_name, args.stdio_cmd, args.stdio_args)

    # Register key tools (names must match server tool names)
    tool_names = [
        "promptyoself_schedule_time",
        "promptyoself_schedule_cron",
        "promptyoself_schedule_every",
        "promptyoself_list",
        "promptyoself_cancel",
        "promptyoself_execute",
        "promptyoself_test",
        "promptyoself_agents",
        "promptyoself_upload",
        "promptyoself_set_default_agent",
        "promptyoself_set_scoped_default_agent",
        "promptyoself_get_scoped_default_agent",
        "promptyoself_inference_diagnostics",
        "health",
    ]
    add_tools_for_server(client, args.server_name, tool_names)

    # Fetch tool IDs and attach all to the agent
    name_to_id = list_server_tool_ids(client, args.server_name)
    attach_tools_to_agent(client, args.agent_id, list(name_to_id.values()))

    if args.send_message:
        send_test_message(client, args.agent_id, args.server_name)

    print("Setup complete.")


if __name__ == "__main__":
    main()

