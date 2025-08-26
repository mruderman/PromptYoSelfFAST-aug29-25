#!/usr/bin/env python3
"""
PromptYoSelf MCP Server (FastMCP)

This server exposes the PromptYoSelf CLI plugin's functionality as MCP tools.
It directly imports the underlying CLI functions (rather than shelling out),
so it remains lightweight and reliable while preserving all existing behavior.

Transports supported:
- stdio (default)
- http (recommended for remote clients)
- sse  (legacy/optional)

Run examples:
- STDIO (local tools):        python promptyoself_mcp_server.py
- HTTP on 127.0.0.1:8000:     python promptyoself_mcp_server.py --transport http --host 127.0.0.1 --port 8000 --path /mcp
- SSE on 127.0.0.1:8000:      python promptyoself_mcp_server.py --transport sse  --host 127.0.0.1 --port 8000

Environment:
- LETTA_BASE_URL (default http://localhost:8283)
- LETTA_API_KEY or LETTA_SERVER_PASSWORD
- PROMPTYOSELF_DB (defaults to promptyoself.db if not set in plugin)
"""

from __future__ import annotations

import os
import json
import logging
import argparse
from typing import Any, Dict, Optional

from fastmcp import FastMCP, Context

# Import PromptYoSelf CLI module functions (direct, not subprocess)
from smcp.plugins.promptyoself import cli as pys_cli

# Map CLI functions
_register_prompt = pys_cli.register_prompt
_list_prompts = pys_cli.list_prompts
_cancel_prompt = pys_cli.cancel_prompt
_execute_prompts = pys_cli.execute_prompts
_test_connection = pys_cli.test_connection
_list_agents = pys_cli.list_agents
_upload_tool = pys_cli.upload_tool

# Configure basic logging for the server process
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("promptyoself-mcp-server")

mcp = FastMCP(
    name="PromptYoSelf MCP Server",
    instructions=(
        "Expose PromptYoSelf scheduling, execution, and Letta integration via MCP tools. "
        "Provides register, list, cancel, execute, test, agents, and upload functions."
    ),
)


@mcp.tool
async def promptyoself_register(
    agent_id: str,
    prompt: str,
    time: Optional[str] = None,
    cron: Optional[str] = None,
    every: Optional[str] = None,
    skip_validation: bool = False,
    max_repetitions: Optional[int] = None,
    start_at: Optional[str] = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """
    Register a new scheduled prompt for a Letta agent.

    Args:
        agent_id: Target Letta agent ID.
        prompt: Prompt text to be delivered.
        time: ISO datetime for one-time schedule (e.g. 2025-12-25T10:00:00).
        cron: Cron expression for recurring schedule (e.g. "0 9 * * *").
        every: Interval expression (e.g. "30s", "5m", "1h").
        skip_validation: If true, skip agent existence validation.
        max_repetitions: Optional max repeat count for interval schedules.
        start_at: ISO datetime when interval schedules should begin.

    Returns:
        JSON dict with status, id, next_run, message or error.
    """
    args = {
        "agent_id": agent_id,
        "prompt": prompt,
        "time": time,
        "cron": cron,
        "every": every,
        "skip_validation": skip_validation,
        "max_repetitions": max_repetitions,
        "start_at": start_at,
    }
    try:
        if ctx:
            await ctx.info(f"Registering prompt for agent={agent_id}")
        return _register_prompt(args)
    except Exception as e:
        logger.exception("promptyoself_register failed")
        return {"error": f"Registration failed: {e}"}


@mcp.tool
async def promptyoself_list(
    agent_id: Optional[str] = None,
    include_cancelled: bool = False,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """
    List scheduled prompts, optionally filtered by agent.

    Args:
        agent_id: Optional agent filter.
        include_cancelled: If true, include cancelled schedules.

    Returns:
        JSON dict with status, schedules, count or error.
    """
    args = {
        "agent_id": agent_id,
        # CLI expects key 'all' to include cancelled
        "all": include_cancelled,
    }
    try:
        if ctx:
            await ctx.info(f"Listing schedules (agent_id={agent_id}, include_cancelled={include_cancelled})")
        return _list_prompts(args)
    except Exception as e:
        logger.exception("promptyoself_list failed")
        return {"error": f"List failed: {e}"}


@mcp.tool
async def promptyoself_cancel(
    schedule_id: int,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """
    Cancel a scheduled prompt by ID.

    Args:
        schedule_id: Numeric ID of the schedule to cancel.

    Returns:
        JSON dict with status, cancelled_id or error.
    """
    args = {"id": schedule_id}
    try:
        if ctx:
            await ctx.info(f"Cancelling schedule_id={schedule_id}")
        return _cancel_prompt(args)
    except Exception as e:
        logger.exception("promptyoself_cancel failed")
        return {"error": f"Cancel failed: {e}"}


@mcp.tool
async def promptyoself_execute(
    loop: bool = False,
    interval: int = 60,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """
    Execute due prompts once or run in loop mode.

    Args:
        loop: Run scheduler loop if true; otherwise execute once.
        interval: Loop interval in seconds (used when loop=True).

    Returns:
        JSON dict indicating execution results or error.
    """
    args = {
        "loop": loop,
        "interval": interval,
    }
    try:
        if ctx:
            await ctx.info(f"Executing prompts (loop={loop}, interval={interval}s)")
        return _execute_prompts(args)
    except Exception as e:
        logger.exception("promptyoself_execute failed")
        return {"error": f"Execute failed: {e}"}


@mcp.tool
async def promptyoself_test(ctx: Context | None = None) -> Dict[str, Any]:
    """
    Test connectivity with the Letta server.

    Returns:
        JSON dict with connectivity status or error.
    """
    try:
        if ctx:
            await ctx.info("Testing Letta connectivity")
        return _test_connection({})
    except Exception as e:
        logger.exception("promptyoself_test failed")
        return {"error": f"Test failed: {e}"}


@mcp.tool
async def promptyoself_agents(ctx: Context | None = None) -> Dict[str, Any]:
    """
    List available Letta agents.

    Returns:
        JSON dict with agents list or error.
    """
    try:
        if ctx:
            await ctx.info("Listing Letta agents")
        return _list_agents({})
    except Exception as e:
        logger.exception("promptyoself_agents failed")
        return {"error": f"Agents listing failed: {e}"}


@mcp.tool
async def promptyoself_upload(
    source_code: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """
    Upload a Letta-native tool from complete Python source code.

    Args:
        source_code: Complete top-level Python function with docstring and type hints.
        name: Optional reference name for logs (Letta derives actual tool name).
        description: Optional tool description metadata.

    Returns:
        JSON dict indicating success with tool_id/name, or error.
    """
    args = {
        "name": name,
        "description": description,
        "source_code": source_code,
    }
    try:
        if ctx:
            await ctx.info("Uploading Letta-native tool from source code")
        return _upload_tool(args)
    except Exception as e:
        logger.exception("promptyoself_upload failed")
        return {"error": f"Upload failed: {e}"}


@mcp.tool
async def health(ctx: Context | None = None) -> Dict[str, Any]:
    """
    Server health and configuration summary.

    Returns:
        JSON dict with status and relevant configuration hints.
    """
    try:
        cfg = {
            "status": "healthy",
            "letta_base_url": os.getenv("LETTA_BASE_URL", "http://localhost:8283"),
            "db": os.getenv("PROMPTYOSELF_DB", "promptyoself.db"),
            "auth_set": bool(os.getenv("LETTA_API_KEY") or os.getenv("LETTA_SERVER_PASSWORD")),
        }
        if ctx:
            await ctx.info(f"Health check: {json.dumps(cfg)}")
        return cfg
    except Exception as e:
        logger.exception("health check failed")
        return {"error": f"Health check failed: {e}"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PromptYoSelf MCP Server (FastMCP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # STDIO (default)
  python promptyoself_mcp_server.py

  # HTTP (recommended for remote clients)
  python promptyoself_mcp_server.py --transport http --host 127.0.0.1 --port 8000 --path /mcp

  # SSE (legacy)
  python promptyoself_mcp_server.py --transport sse --host 127.0.0.1 --port 8000
""",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default=os.getenv("FASTMCP_TRANSPORT", "stdio"),
        help="Transport to use (default: stdio)",
    )
    parser.add_argument("--host", default=os.getenv("FASTMCP_HOST", "127.0.0.1"), help="Host for HTTP/SSE")
    parser.add_argument("--port", type=int, default=int(os.getenv("FASTMCP_PORT", "8000")), help="Port for HTTP/SSE")
    parser.add_argument("--path", default=os.getenv("FASTMCP_PATH", "/mcp"), help="Path for HTTP")
    parser.add_argument("--log-level", default=os.getenv("FASTMCP_LOG_LEVEL", None), help="Override server log level")
    args = parser.parse_args()

    logger.info("Starting PromptYoSelf MCP Server", extra={"transport": args.transport})

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "http":
        # streamable-http or http are supported; use "http" for simplicity here
        mcp.run(transport="http", host=args.host, port=args.port, path=args.path, log_level=args.log_level)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        raise ValueError(f"Unsupported transport: {args.transport}")


if __name__ == "__main__":
    main()