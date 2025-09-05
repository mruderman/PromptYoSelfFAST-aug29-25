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
- PROMPTYOSELF_DB (defaults to a persistent path if available; see start.sh)
"""

from __future__ import annotations

import os
import json
import logging
import argparse
from typing import Any, Dict, Optional

try:
    from fastmcp import FastMCP, Context
    from fastmcp.tools.tool import ToolResult
except ImportError:  # Make import tolerant for environments without fastmcp
    class Context:  # minimal placeholder
        pass

    class _DummyMCP:
        def __init__(self, *args, **kwargs):
            self.name = kwargs.get("name", "Dummy MCP")
            self.instructions = kwargs.get("instructions", "")

        def tool(self, name: str | None = None, output_schema: dict | None = None):
            def _decorator(fn):
                return fn
            return _decorator

        def run(self, *args, **kwargs):
            raise RuntimeError("fastmcp not installed; cannot run transports")

    class ToolResult:  # placeholder for type hints
        pass

    FastMCP = _DummyMCP

# Import PromptYoSelf CLI module functions (direct, not subprocess)
from promptyoself import cli as pys_cli
from promptyoself.db import get_db_file as _pys_get_db_file

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

# In-memory per-client/session default agent mapping
_SCOPED_AGENT_DEFAULTS: dict[str, str] = {}

# Optional background executor process handle
_EXECUTOR_PROCESS = None  # type: ignore[assignment]

def _start_executor_loop_if_enabled() -> None:
    """Optionally start the scheduler execute loop in a background process.

    Controlled by env PROMPTYOSELF_EXECUTOR_AUTOSTART=true/1 and interval
    PROMPTYOSELF_EXECUTOR_INTERVAL (default 60 seconds).
    """
    # Opt-out by default: autostart unless explicitly disabled
    autostart = os.getenv("PROMPTYOSELF_EXECUTOR_AUTOSTART", "true").lower() in ("1", "true", "yes")
    if not autostart:
        return
    try:
        interval = int(os.getenv("PROMPTYOSELF_EXECUTOR_INTERVAL", "60"))
    except Exception:
        interval = 60
    try:
        import multiprocessing as _mp
        def _runner():
            try:
                args = {"loop": True, "interval": interval}
                _execute_prompts(args)  # blocks loop internally
            except Exception as exc:  # pragma: no cover (background)
                logger.exception("Background executor loop crashed: %s", exc)
        global _EXECUTOR_PROCESS
        _EXECUTOR_PROCESS = _mp.Process(target=_runner, daemon=True)
        _EXECUTOR_PROCESS.start()
        logger.info("Started background executor loop", extra={"interval": interval})
    except Exception as exc:  # pragma: no cover (background)
        logger.exception("Failed to start background executor loop: %s", exc)


@mcp.tool(name="promptyoself_executor_status")
async def _promptyoself_executor_status_tool(
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Return background executor loop status (running and interval)."""
    try:
        running = bool(_EXECUTOR_PROCESS is not None and getattr(_EXECUTOR_PROCESS, "is_alive", lambda: False)())
        try:
            interval = int(os.getenv("PROMPTYOSELF_EXECUTOR_INTERVAL", "60"))
        except Exception:
            interval = None
        return {"status": "ok", "running": running, "interval": interval}
    except Exception as e:
        logger.exception("executor_status failed")
        return {"error": f"Status failed: {e}"}


def _get_ctx_scope_key(ctx: Optional[Context]) -> Optional[str]:
    """Derive a stable-ish scope key for per-client defaults.

    Tries multiple attributes from ctx and ctx.request_context, using the
    first non-empty string found among: request_context.session_id,
    ctx.session_id, request_context.client_id, ctx.client_id.
    """
    if ctx is None:
        return None
    try:
        rc = getattr(ctx, "request_context", None)
    except Exception:
        rc = None

    candidates = []
    if rc is not None:
        for name in ("session_id", "client_id"):
            try:
                val = getattr(rc, name, None)
                if isinstance(val, str) and val.strip():
                    candidates.append(val.strip())
            except Exception:
                pass
    for name in ("session_id", "client_id"):
        try:
            val = getattr(ctx, name, None)
            if isinstance(val, str) and val.strip():
                candidates.append(val.strip())
        except Exception:
            pass
    return candidates[0] if candidates else None

# JSON Schema definition for tool outputs 
# Note: FastMCP requires output schemas to be type "object", not "oneOf"
SCHEDULE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        # Success response fields
        "status": {
            "type": "string",
            "enum": ["success"],
            "description": "Operation status indicator (present on success)"
        },
        "id": {
            "type": "integer",
            "description": "Unique schedule ID for future reference (present on success)"
        },
        "next_run": {
            "type": "string",
            "format": "date-time",
            "description": "ISO 8601 datetime when the prompt will first execute (present on success)"
        },
        "message": {
            "type": "string",
            "description": "Human-readable success confirmation (present on success)"
        },
        # Error response field
        "error": {
            "type": "string",
            "description": "Error message explaining what went wrong (present on error)"
        }
    },
    "additionalProperties": False,
    # Note: We can't use "required" with this combined approach since either success OR error fields will be present
    "description": "Returns either success fields (status, id, next_run, message) or error field"
}


def _infer_agent_id(ctx: Context | None = None) -> tuple[Optional[str], Dict[str, Any]]:
    """Best-effort inference of the caller's agent_id.

    Order of attempts:
    1) Context metadata (if provided by client/transport)
    2) Environment variables (PROMPTYOSELF_DEFAULT_AGENT_ID, LETTA_AGENT_ID, LETTA_DEFAULT_AGENT_ID)
    3) Single-agent fallback (if PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK=true and exactly one agent exists)

    Returns (agent_id_or_none, debug_info)
    """
    debug: Dict[str, Any] = {
        "source": None,
        "context_metadata_keys": [],
        "env_checked": {
            "PROMPTYOSELF_DEFAULT_AGENT_ID": False,
            "LETTA_AGENT_ID": False,
            "LETTA_DEFAULT_AGENT_ID": False,
        },
        "single_agent_fallback": False,
        "agents_count": None,
    }

    # We allow fallback to env/single-agent even when ctx is present
    # if we couldn't extract an agent_id from the context. This matches
    # real-world clients that attach an empty ctx without metadata.

    # 1) Context metadata (non-breaking, best-effort; attributes may not exist)
    if ctx is not None:
        # 1a) Some clients (e.g., Letta) embed metadata on a nested request_context
        # Check request_context FIRST as it should take priority over regular context
        try:
            req_ctx = getattr(ctx, "request_context", None)
            if req_ctx is not None:
                # Probe common metadata attributes on request_context
                for attr_name in ("metadata", "meta", "request_metadata", "call_metadata"):
                    try:
                        rc_meta = getattr(req_ctx, attr_name, None)
                    except Exception:
                        rc_meta = None
                    if rc_meta is None:
                        continue
                    # Normalize to dict
                    if not isinstance(rc_meta, dict):
                        try:
                            rc_meta = dict(rc_meta)  # type: ignore[arg-type]
                        except Exception:
                            try:
                                rc_meta = vars(rc_meta)  # type: ignore[assignment]
                            except Exception:
                                rc_meta = None
                    if not isinstance(rc_meta, dict):
                        continue
                    # Look for direct keys (presence matters)
                    for key in ("agent_id", "agentId", "letta_agent_id", "caller_agent_id"):
                        if key in rc_meta:
                            val = rc_meta.get(key)
                            if isinstance(val, str) and val.strip():
                                debug.update({"source": f"context.request_context.{attr_name}", "key": key})
                                return val.strip(), debug
                            else:
                                debug.update({"source": None})
                                return None, debug
                    # Look for nested agent objects
                    for key in ("agent", "caller", "source_agent"):
                        container = rc_meta.get(key)
                        if isinstance(container, dict):
                            for sub in ("agent_id", "id", "agentId"):
                                if sub in container:
                                    subval = container.get(sub)
                                    if isinstance(subval, str) and subval.strip():
                                        debug.update({"source": f"context.request_context.{attr_name}.nested", "key": f"{key}.{sub}"})
                                        return subval.strip(), debug
                                    else:
                                        debug.update({"source": None})
                                        return None, debug
        except Exception:
            # Ignore request_context probing errors
            pass

        # 1b) Regular context metadata (checked after request_context)
        try:
            # Commonly used metadata keys we might get from clients
            meta = getattr(ctx, "metadata", None)
            # If metadata is an object, try to turn it into a dict-like mapping of attributes
            if meta is not None and not isinstance(meta, dict):
                try:
                    meta = dict(meta)  # type: ignore[arg-type]
                except Exception:
                    try:
                        meta = vars(meta)  # type: ignore[assignment]
                    except Exception:
                        meta = None

            if isinstance(meta, dict):
                try:
                    debug["context_metadata_keys"] = sorted(list(meta.keys()))[:20]
                except Exception:
                    pass
                # Direct keys: detect presence first; if present but invalid, short-circuit with None
                for key in ("agent_id", "agentId", "letta_agent_id", "caller_agent_id"):
                    if key in meta:
                        val = meta.get(key)
                        if isinstance(val, str) and val.strip():
                            debug.update({"source": "context.metadata", "key": key})
                            return val.strip(), debug
                        else:
                            # Key present but invalid/null/empty/non-string – do not fallback
                            debug.update({"source": None})
                            return None, debug
                # Nested structures that might contain an agent id
                for key in ("agent", "caller", "source_agent"):
                    container = meta.get(key)
                    if isinstance(container, dict):
                        for sub in ("agent_id", "id", "agentId"):
                            if sub in container:
                                subval = container.get(sub)
                                if isinstance(subval, str) and subval.strip():
                                    debug.update({"source": "context.metadata.nested", "key": f"{key}.{sub}"})
                                    return subval.strip(), debug
                                else:
                                    debug.update({"source": None})
                                    return None, debug

            # Direct attribute (best-effort, non-blocking if invalid)
            # Some context objects (e.g., unittest.mock.Mock) report attributes
            # for any name. Only treat this as a signal when it's a non-empty string.
            try:
                direct = getattr(ctx, "agent_id", None)
            except Exception:
                direct = None
            if isinstance(direct, str) and direct.strip():
                debug.update({"source": "context.attr", "key": "agent_id"})
                return direct.strip(), debug
            # If the attribute exists but is not a usable string, ignore it and
            # continue with other inference methods (env, single-agent, etc.).
        except Exception as _:
            # Ignore context probing errors
            pass

    # 1c) Per-client/session scoped default (if set via tool)
    try:
        scope_key = _get_ctx_scope_key(ctx)
        if scope_key and scope_key in _SCOPED_AGENT_DEFAULTS:
            agent_id = _SCOPED_AGENT_DEFAULTS.get(scope_key)
            if agent_id:
                debug.update({"source": "scoped-default", "scope": scope_key})
                return agent_id, debug
    except Exception:
        pass

    # If no agent_id found in context or scoped defaults, continue to environment fallback

    # 2) Environment variables
    env_vals = {}
    for env_key in ("PROMPTYOSELF_DEFAULT_AGENT_ID", "LETTA_AGENT_ID", "LETTA_DEFAULT_AGENT_ID"):
        val = os.getenv(env_key)
        env_vals[env_key] = val
        debug["env_checked"][env_key] = bool(val and val.strip())
    for env_key, val in env_vals.items():
        if val and val.strip():
            debug.update({"source": "env", "key": env_key})
            return val.strip(), debug

    # 2a) Additional permissive env names (do not add to env_checked to preserve test expectations)
    for alt_key in ("AGENT_ID", "DEFAULT_AGENT_ID"):
        val = os.getenv(alt_key)
        if val and val.strip():
            debug.update({"source": "env", "key": alt_key})
            return val.strip(), debug

    # 3) Single-agent fallback (opt-in)
    use_single = os.getenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false").lower() in ("1", "true", "yes")
    if use_single:
        try:
            # Use underlying CLI wrapper to list agents (avoids import cycles)
            result = _list_agents({})
            if isinstance(result, dict) and result.get("status") == "success":
                agents = result.get("agents") or []
                try:
                    debug["agents_count"] = len(agents) if isinstance(agents, list) else None
                except Exception:
                    pass
                if isinstance(agents, list) and len(agents) == 1:
                    only = agents[0]
                    agent_id = only.get("id") if isinstance(only, dict) else None
                    if agent_id:
                        debug.update({"source": "single-agent-fallback"})
                        debug["single_agent_fallback"] = True
                        return agent_id, debug
        except Exception:
            pass
    else:
        debug["single_agent_fallback"] = False

    debug.update({"source": None})
    return None, debug


async def promptyoself_register(
    agent_id: Optional[str],
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
    Register a new scheduled prompt for yourself. Exactly one of time, cron, or every must be provided. Make sure to include you own own agent ID.

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
        # Allow auto-inference if agent_id not provided (use ctx when available)
        if not agent_id or not str(agent_id).strip():
            inferred, debug = _infer_agent_id(ctx)
            agent_id = inferred
            if not agent_id:
                env_present = [k for k, present in (debug.get("env_checked") or {}).items() if present]
                ctx_keys = ",".join((debug.get("context_metadata_keys") or [])[:10])
                single_flag = "on" if debug.get("single_agent_fallback") else "off"
                hint = (
                    "Provide agent_id explicitly, or set one of "
                    "PROMPTYOSELF_DEFAULT_AGENT_ID/LETTA_AGENT_ID/LETTA_DEFAULT_AGENT_ID. "
                    "If calling via Letta MCP, ensure ctx.metadata.agent_id is passed. "
                    "Check CLIENT_DEBUGGING.md for MCP client troubleshooting steps."
                )
                return {"error": (
                    "agent_id is required and could not be inferred "
                    f"(source={debug.get('source')}; ctx_keys=[{ctx_keys}]; "
                    f"env_present={env_present}; single_agent_fallback={single_flag}). "
                    + hint
                )}

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



## General scheduling tool removed to reduce ambiguity; use strict variants below


# Strict variants to enable ADE strict mode and simpler schemas
@mcp.tool(name="promptyoself_schedule_time", output_schema=SCHEDULE_OUTPUT_SCHEMA)
async def _promptyoself_schedule_time_tool(
        prompt: str,
        time: str,
        agent_id: Optional[str] = None,
        # Pass-throughs from some clients/routers – accepted and ignored
        mcp_server_id: Optional[str] = None,
        mcp_server_name: Optional[str] = None,
        request_heartbeat: Optional[bool] = None,
        heartbeat: Optional[bool] = None,
        skip_validation: bool = False,
        ctx: Context | None = None,
) -> Dict[str, Any]:
        """Schedule a one-time prompt at an exact datetime.

        Inputs:
        - agent_id: Your Letta agent ID (e.g., "agt_123...").
        - prompt: The message to deliver.
        - time: ISO 8601 datetime in the future. Accepted forms:
            - 2025-08-31T09:50:22Z (UTC)
            - 2025-08-31T09:50:22+00:00 (offset)
            - 2025-08-31 09:50:22 UTC (normalized to Z)
        - skip_validation: If true, skip checking that agent_id exists.

        Rule: This variant only accepts a one-time datetime.

        Example:
        {
            "agent_id": "agt_abc123",
            "prompt": "Ping me once",
            "time": "2025-12-25T10:00:00Z"
        }
        """
        # Enhanced debugging for agent_id parameter handling
        logger.debug("promptyoself_schedule_time called", extra={
            "agent_id_raw": repr(agent_id),
            "agent_id_type": type(agent_id).__name__,
            "agent_id_truthy": bool(agent_id),
            "prompt_length": len(prompt) if prompt else 0,
            "time": time,
            "skip_validation": skip_validation
        })

        # Normalize agent_id handling - treat string "None" as None
        if agent_id is not None and str(agent_id).strip().lower() in ("none", "null", ""):
            logger.warning("Converting string 'None'/'null'/empty to actual None", extra={
                "original_agent_id": repr(agent_id)
            })
            agent_id = None

        # Infer if needed
        if not agent_id or not str(agent_id).strip():
            inferred, debug_info = _infer_agent_id(ctx)
            logger.info("Agent ID inference attempted", extra={
                "inferred_agent_id": inferred,
                "inference_debug": debug_info
            })
            agent_id = inferred

        return await promptyoself_register(
                agent_id=agent_id,
                prompt=prompt,
                time=time,
                skip_validation=skip_validation,
                ctx=ctx,
        )


@mcp.tool(name="promptyoself_schedule_cron", output_schema=SCHEDULE_OUTPUT_SCHEMA)
async def _promptyoself_schedule_cron_tool(
        prompt: str,
        cron: str,
        agent_id: Optional[str] = None,
        # Pass-throughs from some clients/routers – accepted and ignored
        mcp_server_id: Optional[str] = None,
        mcp_server_name: Optional[str] = None,
        request_heartbeat: Optional[bool] = None,
        heartbeat: Optional[bool] = None,
        skip_validation: bool = False,
        ctx: Context | None = None,
) -> Dict[str, Any]:
        """Schedule a recurring prompt using a cron expression.

        Inputs:
        - agent_id: Your Letta agent ID (e.g., "agt_123...").
        - prompt: The message to deliver.
        - cron: Standard 5-field cron ("m h dom mon dow"). Examples:
            - "0 9 * * *" (every day at 09:00)
            - "*/15 * * * *" (every 15 minutes)
            - "0 9 * * MON-FRI" (weekdays at 09:00) if your cron parser supports names.
        - skip_validation: If true, skip checking that agent_id exists.

        Rule: This variant only accepts cron.

        Example:
        {
            "agent_id": "agt_abc123",
            "prompt": "Daily standup",
            "cron": "0 9 * * *"
        }
        """
        # Normalize agent_id handling - treat string "None" as None
        if agent_id is not None and str(agent_id).strip().lower() in ("none", "null", ""):
            agent_id = None
        
        # Infer if needed
        if not agent_id or not str(agent_id).strip():
            inferred, _debug = _infer_agent_id(ctx)
            agent_id = inferred

        return await promptyoself_register(
                agent_id=agent_id,
                prompt=prompt,
                cron=cron,
                skip_validation=skip_validation,
                ctx=ctx,
        )


@mcp.tool(name="promptyoself_schedule_every", output_schema=SCHEDULE_OUTPUT_SCHEMA)
async def _promptyoself_schedule_every_tool(
        prompt: str,
        every: str,
        start_at: Optional[str] = None,
        max_repetitions: Optional[int] = None,
        agent_id: Optional[str] = None,
        # Pass-throughs from some clients/routers – accepted and ignored
        mcp_server_id: Optional[str] = None,
        mcp_server_name: Optional[str] = None,
        request_heartbeat: Optional[bool] = None,
        heartbeat: Optional[bool] = None,
        skip_validation: bool = False,
        ctx: Context | None = None,
) -> Dict[str, Any]:
        """Schedule a repeating prompt using an interval.

        Inputs:
        - agent_id: Your Letta agent ID (e.g., "agt_123...").
        - prompt: The message to deliver.
        - every: Interval like "30s", "5m", or "1h" (integer seconds allowed, e.g., "45").
        - start_at: Optional ISO 8601 datetime to begin the interval; must be in the future.
        - max_repetitions: Optional positive integer cap on repeats.
        - skip_validation: If true, skip checking that agent_id exists.

        Rule: This variant only accepts an interval.

        Example:
        {
            "agent_id": "agt_abc123",
            "prompt": "Focus check",
            "every": "30m",
            "start_at": "2025-01-02T15:00:00Z",
            "max_repetitions": 10
        }
        """
        # Normalize agent_id handling - treat string "None" as None
        if agent_id is not None and str(agent_id).strip().lower() in ("none", "null", ""):
            agent_id = None
        
        # Infer if needed
        if not agent_id or not str(agent_id).strip():
            inferred, _debug = _infer_agent_id(ctx)
            agent_id = inferred

        return await promptyoself_register(
                agent_id=agent_id,
                prompt=prompt,
                every=every,
                start_at=start_at,
                max_repetitions=max_repetitions,
                skip_validation=skip_validation,
                ctx=ctx,
        )


## Note: No 'promptyoself_register' tool is exported to avoid naming confusion.


@mcp.tool
async def promptyoself_list(
    agent_id: Optional[str] = None,
    include_cancelled: bool = False,
    # Pass-throughs from some clients/routers – accepted and ignored
    mcp_server_id: Optional[str] = None,
    mcp_server_name: Optional[str] = None,
    request_heartbeat: Optional[bool] = None,
    heartbeat: Optional[bool] = None,
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
    # Pass-throughs from some clients/routers – accepted and ignored
    mcp_server_id: Optional[str] = None,
    mcp_server_name: Optional[str] = None,
    request_heartbeat: Optional[bool] = None,
    heartbeat: Optional[bool] = None,
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
    # Pass-throughs
    mcp_server_id: Optional[str] = None,
    mcp_server_name: Optional[str] = None,
    request_heartbeat: Optional[bool] = None,
    heartbeat: Optional[bool] = None,
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
async def promptyoself_test(
    # Pass-throughs
    mcp_server_id: Optional[str] = None,
    mcp_server_name: Optional[str] = None,
    request_heartbeat: Optional[bool] = None,
    heartbeat: Optional[bool] = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
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
async def promptyoself_agents(
    # Pass-throughs
    mcp_server_id: Optional[str] = None,
    mcp_server_name: Optional[str] = None,
    request_heartbeat: Optional[bool] = None,
    heartbeat: Optional[bool] = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
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
    # Pass-throughs
    mcp_server_id: Optional[str] = None,
    mcp_server_name: Optional[str] = None,
    request_heartbeat: Optional[bool] = None,
    heartbeat: Optional[bool] = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Upload a Letta-native tool from complete Python source code."""
    return await promptyoself_upload(
        source_code=source_code,
        name=name,
        description=description,
    )


@mcp.tool(name="promptyoself_set_default_agent")
async def _promptyoself_set_default_agent_tool(
    agent_id: str,
    # Pass-throughs
    mcp_server_id: Optional[str] = None,
    mcp_server_name: Optional[str] = None,
    request_heartbeat: Optional[bool] = None,
    heartbeat: Optional[bool] = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Set the default agent ID to avoid having to pass it with every call.
    
    This sets the LETTA_AGENT_ID environment variable for the current session.
    
    Args:
        agent_id: The agent ID to set as default
    
    Returns:
        JSON dict with status and confirmation
    """
    try:
        if not agent_id or not agent_id.strip():
            return {"error": "agent_id cannot be empty"}
        
        # Set the environment variable
        os.environ["LETTA_AGENT_ID"] = agent_id.strip()
        
        # Verify it was set correctly
        verification = os.getenv("LETTA_AGENT_ID")
        
        return {
            "status": "success",
            "message": f"Default agent ID set to: {verification}",
            "agent_id": verification,
            "note": "This setting only applies to the current server session"
        }
    except Exception as e:
        logger.exception("Failed to set default agent ID")
        return {"error": f"Failed to set default agent ID: {e}"}


@mcp.tool(name="promptyoself_set_scoped_default_agent")
async def _promptyoself_set_scoped_default_agent_tool(
    agent_id: str,
    # Pass-throughs
    mcp_server_id: Optional[str] = None,
    mcp_server_name: Optional[str] = None,
    request_heartbeat: Optional[bool] = None,
    heartbeat: Optional[bool] = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Set a per-client/session default agent ID.

    This associates the given agent_id with the caller's session/client identity
    (derived from ctx.request_context.session_id/client_id or ctx.session_id/client_id).

    Only affects requests from the same client/session; does not modify process-wide env.
    """
    try:
        if not agent_id or not agent_id.strip():
            return {"error": "agent_id cannot be empty"}
        scope_key = _get_ctx_scope_key(ctx)
        if not scope_key:
            return {"error": "Unable to derive a client/session identity from context; cannot set scoped default"}
        _SCOPED_AGENT_DEFAULTS[scope_key] = agent_id.strip()
        return {
            "status": "success",
            "message": f"Scoped default agent set for {scope_key}",
            "agent_id": _SCOPED_AGENT_DEFAULTS[scope_key],
        }
    except Exception as e:
        logger.exception("Failed to set scoped default agent ID")
        return {"error": f"Failed to set scoped default agent ID: {e}"}


@mcp.tool(name="promptyoself_get_scoped_default_agent")
async def _promptyoself_get_scoped_default_agent_tool(
    # Pass-throughs
    mcp_server_id: Optional[str] = None,
    mcp_server_name: Optional[str] = None,
    request_heartbeat: Optional[bool] = None,
    heartbeat: Optional[bool] = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Get the scoped default agent ID for the current client/session, if any."""
    try:
        scope_key = _get_ctx_scope_key(ctx)
        if not scope_key:
            return {"status": "ok", "scope": None, "agent_id": None}
        return {"status": "ok", "scope": scope_key, "agent_id": _SCOPED_AGENT_DEFAULTS.get(scope_key)}
    except Exception as e:
        logger.exception("Failed to get scoped default agent ID")
        return {"error": f"Failed to get scoped default agent ID: {e}"}


@mcp.tool(name="promptyoself_inference_diagnostics")
async def _promptyoself_inference_diagnostics_tool(
    # Pass-throughs
    mcp_server_id: Optional[str] = None,
    mcp_server_name: Optional[str] = None,
    request_heartbeat: Optional[bool] = None,
    heartbeat: Optional[bool] = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """Report how agent_id inference would behave for this request.

    Returns keys: ctx_present, ctx_metadata_keys, ctx_agent_id_attr, env, single_agent_fallback_enabled, agents_count.
    """
    info: Dict[str, Any] = {
        "status": "ok",
        "ctx_present": bool(ctx is not None),
        "ctx_metadata_keys": [],
        "ctx_agent_id_attr": None,
        "env": {
            "PROMPTYOSELF_DEFAULT_AGENT_ID": {
                "set": bool(os.getenv("PROMPTYOSELF_DEFAULT_AGENT_ID")),
                "value": os.getenv("PROMPTYOSELF_DEFAULT_AGENT_ID")
            },
            "LETTA_AGENT_ID": {
                "set": bool(os.getenv("LETTA_AGENT_ID")),
                "value": os.getenv("LETTA_AGENT_ID")
            },
            "LETTA_DEFAULT_AGENT_ID": {
                "set": bool(os.getenv("LETTA_DEFAULT_AGENT_ID")),
                "value": os.getenv("LETTA_DEFAULT_AGENT_ID")
            },
        },
        "single_agent_fallback_enabled": os.getenv("PROMPTYOSELF_USE_SINGLE_AGENT_FALLBACK", "false").lower() in ("1", "true", "yes"),
        "agents_count": None,
    }

    # Context metadata keys and attr
    if ctx is not None:
        try:
            meta = getattr(ctx, "metadata", None)
            if meta is not None and not isinstance(meta, dict):
                try:
                    meta = dict(meta)  # type: ignore[arg-type]
                except Exception:
                    try:
                        meta = vars(meta)
                    except Exception:
                        meta = None
            if isinstance(meta, dict):
                try:
                    info["ctx_metadata_keys"] = sorted(list(meta.keys()))[:20]
                except Exception:
                    pass
        except Exception:
            pass

        try:
            direct = getattr(ctx, "agent_id", None)
            if isinstance(direct, str) and direct.strip():
                info["ctx_agent_id_attr"] = direct.strip()
        except Exception:
            pass

    # Agent count if fallback enabled
    if info["single_agent_fallback_enabled"]:
        try:
            res = _list_agents({})
            if isinstance(res, dict) and res.get("status") == "success":
                agents = res.get("agents") or []
                info["agents_count"] = len(agents) if isinstance(agents, list) else None
        except Exception:
            pass

    # Also return the decision of _infer_agent_id for this ctx
    inferred, debug = _infer_agent_id(ctx)
    info["inferred_agent_id"] = inferred
    info["inference_debug"] = debug

    return info


async def health() -> Dict[str, Any]:
    """
    Server health and configuration summary.

    Returns:
        JSON dict with status and relevant configuration hints.
    """
    # Resolve effective DB path via shared DB module, not raw env
    try:
        db_path = _pys_get_db_file()
    except Exception:
        db_path = os.getenv("PROMPTYOSELF_DB", "promptyoself.db")

    return {
        "status": "healthy",
        "letta_base_url": os.getenv("LETTA_BASE_URL", "http://localhost:8283"),
        "db": db_path,
        "auth_set": bool(os.getenv("LETTA_API_KEY") or os.getenv("LETTA_SERVER_PASSWORD")),
        "executor_autostart": os.getenv("PROMPTYOSELF_EXECUTOR_AUTOSTART", "true").lower() in ("1", "true", "yes"),
        "executor_interval": int(os.getenv("PROMPTYOSELF_EXECUTOR_INTERVAL", "60")),
    }


@mcp.tool(name="health")
async def _health_tool(ctx: Context | None = None) -> Dict[str, Any]:
    """Server health and configuration summary."""
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
    parser.add_argument("--autostart-executor", dest="autostart_executor", action="store_true", help="Start background execute loop on launch")
    parser.add_argument("--executor-interval", dest="executor_interval", type=int, default=None, help="Background execute loop interval (seconds)")
    args = parser.parse_args()

    logger.info("Starting PromptYoSelf MCP Server", extra={"transport": args.transport})
    # Soft reminder regarding time sync for correct scheduling
    logger.info(
        "Scheduling uses wall clock time; ensure NTP is synchronized on this host",
        extra={"hint": "Use timedatectl/chrony/ntpd depending on your OS"}
    )

    # Optional background executor
    if getattr(args, "autostart_executor", False):
        os.environ["PROMPTYOSELF_EXECUTOR_AUTOSTART"] = "true"
    if getattr(args, "executor_interval", None) is not None:
        os.environ["PROMPTYOSELF_EXECUTOR_INTERVAL"] = str(args.executor_interval)
    _start_executor_loop_if_enabled()

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
