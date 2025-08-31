#!/usr/bin/env python3
"""
Investigate FastMCP request context to understand metadata handling
"""

import asyncio
import json

try:
    from fastmcp import Client
except ImportError:
    print("FastMCP not available. Installing...")
    import subprocess
    subprocess.run(["pip", "install", "fastmcp"])
    from fastmcp import Client

# Create a simple test tool that explores the context more deeply
from fastmcp import FastMCP

# Create a debug tool
debug_mcp = FastMCP(name="Debug Context")

@debug_mcp.tool(name="debug_context")
async def debug_context_tool(ctx) -> dict:
    """Debug tool to explore context properties"""
    result = {
        "basic_properties": {
            "request_id": getattr(ctx, "request_id", None),
            "client_id": getattr(ctx, "client_id", None),
            "session_id": getattr(ctx, "session_id", None),
        },
        "metadata_exploration": {},
        "request_context_exploration": {}
    }
    
    # Try to access metadata in different ways
    try:
        meta = getattr(ctx, "metadata", None)
        result["metadata_exploration"]["has_metadata_attr"] = meta is not None
        if meta is not None:
            result["metadata_exploration"]["metadata_type"] = type(meta).__name__
            result["metadata_exploration"]["metadata_dir"] = dir(meta)[:10]  # First 10 attrs
    except Exception as e:
        result["metadata_exploration"]["metadata_error"] = str(e)
    
    # Try to access request_context
    try:
        req_ctx = ctx.request_context
        result["request_context_exploration"]["has_request_context"] = req_ctx is not None
        if req_ctx is not None:
            result["request_context_exploration"]["request_context_type"] = type(req_ctx).__name__
            result["request_context_exploration"]["request_context_dir"] = dir(req_ctx)[:15]  # First 15 attrs
            
            # Try to find metadata in request context
            for attr in ["metadata", "meta", "_metadata", "request_metadata", "call_metadata"]:
                try:
                    val = getattr(req_ctx, attr, None)
                    if val is not None:
                        result["request_context_exploration"][f"found_{attr}"] = {
                            "type": type(val).__name__,
                            "value": str(val)[:200]  # Truncate for safety
                        }
                except Exception as e:
                    result["request_context_exploration"][f"error_{attr}"] = str(e)
    except Exception as e:
        result["request_context_exploration"]["request_context_error"] = str(e)
    
    return result

if __name__ == "__main__":
    print("Starting debug server...")
    debug_mcp.run(transport="http", host="127.0.0.1", port=8001, path="/debug")