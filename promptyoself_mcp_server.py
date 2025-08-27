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
from fastmcp.tools.tool import ToolResult

# Import PromptYoSelf CLI module functions (direct, not subprocess)
from promptyoself import cli as pys_cli

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


async def promptyoself_register(
    agent_id: str,
    prompt: str,
    time: Optional[str] = None,
    cron: Optional[str] = None,
    every: Optional[str] = None,
    skip_validation: bool = False,
    max_repetitions: Optional[int] = None,
    start_at: Optional[str] = None,
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
    try:
        # Validation: exactly one of time/cron/every must be provided
        provided = [opt for opt in (time, cron, every) if opt]
        if len(provided) > 1:
            return {"error": "Cannot specify multiple scheduling options"}
        if len(provided) == 0:
            return {"error": "Must specify one of --time, --cron, or --every"}

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
        return _register_prompt(args)
    except Exception as e:
        logger.exception("promptyoself_register failed")
        return {"error": f"Registration failed: {e}"}


@mcp.tool(name="promptyoself_register")
async def _promptyoself_register_tool(
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
    return await promptyoself_register(
        agent_id=agent_id,
        prompt=prompt,
        time=time,
        cron=cron,
        every=every,
        skip_validation=skip_validation,
        max_repetitions=max_repetitions,
        start_at=start_at,
    )


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


async def promptyoself_upload(
    source_code: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
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
    try:
        # Env guard: require either LETTA_API_KEY or LETTA_SERVER_PASSWORD
        if not (os.environ.get("LETTA_API_KEY") or os.environ.get("LETTA_SERVER_PASSWORD")):
            return {"error": "Missing LETTA_API_KEY or LETTA_SERVER_PASSWORD"}

        args = {
            "name": name,
            "description": description,
            "source_code": source_code,
        }
        return _upload_tool(args)
    except Exception as e:
        logger.exception("promptyoself_upload failed")
        return {"error": f"Upload failed: {e}"}


@mcp.tool(name="promptyoself_upload")
async def _promptyoself_upload_tool(
    source_code: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    return await promptyoself_upload(
        source_code=source_code,
        name=name,
        description=description,
    )


async def health() -> Dict[str, Any]:
    """
    Server health and configuration summary.

    Returns:
        JSON dict with status and relevant configuration hints.
    """
    return {
        "status": "healthy",
        "letta_base_url": os.getenv("LETTA_BASE_URL", "http://localhost:8283"),
        "db": os.getenv("PROMPTYOSELF_DB", "promptyoself.db"),
        "auth_set": bool(os.getenv("LETTA_API_KEY") or os.getenv("LETTA_SERVER_PASSWORD")),
    }


@mcp.tool(name="health")
async def _health_tool(ctx: Context | None = None) -> Dict[str, Any]:
    # Return a plain dict so both in-memory and HTTP clients can consume it
    return await health()


# Transport starter wrappers to satisfy unit tests expecting these imports
def serve_stdio_transport() -> None:
    import multiprocessing as _mp
    def _run_stdio():
        mcp.run(transport="stdio")
    p = _mp.Process(target=_run_stdio, daemon=True)
    p.start()

def serve_http_transport(host: str = "127.0.0.1", port: int = 8000, path: str = "/mcp", log_level: Optional[str] = None) -> None:
    import multiprocessing as _mp
    def _run_http():
        try:
            mcp.run(transport="http", host=host, port=port, path=path, log_level=log_level)
        except Exception as exc:
            logger.warning("HTTP transport unavailable (%s), using 'streamable-http'", exc)
            mcp.run(transport="streamable-http", host=host, port=port, path=path, log_level=log_level)
    p = _mp.Process(target=_run_http, daemon=True)
    p.start()

def serve_sse_transport(host: str = "127.0.0.1", port: int = 8000) -> None:
    import multiprocessing as _mp
    def _run_sse():
        mcp.run(transport="sse", host=host, port=port)
    p = _mp.Process(target=_run_sse, daemon=True)
    p.start()

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
        try:
            mcp.run(transport="http", host=args.host, port=args.port, path=args.path, log_level=args.log_level)
        except Exception as exc:
            logger.warning("HTTP transport unavailable (%s), using 'streamable-http'", exc)
            mcp.run(transport="streamable-http", host=args.host, port=args.port, path=args.path, log_level=args.log_level)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        raise ValueError(f"Unsupported transport: {args.transport}")


if __name__ == "__main__":
    main()