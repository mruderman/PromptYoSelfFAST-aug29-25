#!/usr/bin/env python3
"""
Sanctum Letta MCP Server

A Server-Sent Events (SSE) server for orchestrating plugin execution using aiohttp.
Compliant with Model Context Protocol (MCP) specification.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from aiohttp import web, ClientSession
from aiohttp.web import Request, Response, StreamResponse
from aiohttp_cors import setup as cors_setup, ResourceOptions


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Session management
sessions: Dict[str, Dict[str, Any]] = {}

# Plugin registry
plugin_registry: Dict[str, Dict[str, Any]] = {}


def discover_plugins() -> Dict[str, Dict[str, Any]]:
    """Discover available plugins by scanning the plugins directory."""
    plugins_dir_env = os.environ.get("MCP_PLUGINS_DIR")
    if plugins_dir_env:
        plugins_dir = Path(plugins_dir_env)
    else:
        plugins_dir = Path(__file__).parent / "plugins"
    plugins = {}
    
    if not plugins_dir.exists():
        logger.warning(f"Plugins directory not found: {plugins_dir}")
        return plugins
    
    for plugin_dir in plugins_dir.iterdir():
        if plugin_dir.is_dir():
            cli_path = plugin_dir / "cli.py"
            if cli_path.exists():
                plugin_name = plugin_dir.name
                plugins[plugin_name] = {
                    "path": str(cli_path),
                    "commands": {}
                }
                logger.info(f"Discovered plugin: {plugin_name}")
    
    return plugins


def build_tools_manifest() -> List[Dict[str, Any]]:
    """Build the tools manifest in MCP format."""
    tools = []
    logger.info(f"Building tools manifest from {len(plugin_registry)} plugins")
    
    for plugin_name, plugin_info in plugin_registry.items():
        cli_path = plugin_info["path"]
        
        # Get help to extract available commands
        logger.info(f"Getting help for plugin {plugin_name} from {cli_path}")
        try:
            result = subprocess.run(
                [sys.executable, cli_path, "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                help_text = result.stdout
                logger.info(f"Plugin {plugin_name} help output: {help_text[:200]}...")
                lines = help_text.split('\n')
                in_commands_section = False
                for line in lines:
                    if line.strip().startswith("Available commands:"):
                        in_commands_section = True
                        continue
                    if in_commands_section:
                        # End of commands section if we hit an empty line or Examples
                        if not line.strip() or line.strip().startswith("Examples"):
                            in_commands_section = False
                            continue
                        if line.startswith('  '):
                            parts = line.strip().split()
                            if parts and parts[0] not in ['usage:', 'options:', 'Available', 'Examples:']:
                                command = parts[0]
                                properties = {}
                                required = []
                                if command == "click-button":
                                    properties = {
                                        "button-text": {"type": "string", "description": "Text of the button to click"},
                                        "msg-id": {"type": "integer", "description": "Message ID containing the button"}
                                    }
                                    required = ["button-text", "msg-id"]
                                elif command == "send-message":
                                    properties = {
                                        "message": {"type": "string", "description": "Message to send"}
                                    }
                                    required = ["message"]
                                elif command == "deploy":
                                    properties = {
                                        "app-name": {"type": "string", "description": "Name of the application to deploy"},
                                        "environment": {"type": "string", "description": "Deployment environment", "default": "production"}
                                    }
                                    required = ["app-name"]
                                elif command == "rollback":
                                    properties = {
                                        "app-name": {"type": "string", "description": "Name of the application to rollback"},
                                        "version": {"type": "string", "description": "Version to rollback to"}
                                    }
                                    required = ["app-name", "version"]
                                elif command == "status":
                                    properties = {
                                        "app-name": {"type": "string", "description": "Name of the application"}
                                    }
                                    required = ["app-name"]
                                elif command == "workflow-command":
                                    properties = {
                                        "param": {"type": "string", "description": "Parameter for workflow"}
                                    }
                                    required = ["param"]
                                elif command == "test-command":
                                    properties = {}
                                    required = []
                                elif command == "error-command":
                                    properties = {}
                                    required = []
                                elif command == "concurrent-command":
                                    properties = {}
                                    required = []
                                if properties is not None:
                                    tool_name = f"{plugin_name}.{command}"
                                    tools.append({
                                        "name": tool_name,
                                        "description": f"{plugin_name} {command} command",
                                        "inputSchema": {
                                            "type": "object",
                                            "properties": properties,
                                            "required": required
                                        }
                                    })
                                    logger.info(f"Added tool: {tool_name}")
        except Exception as e:
            logger.error(f"Error building tool manifest for {plugin_name}: {e}")
    
    return tools


async def execute_plugin_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a plugin tool command."""
    try:
        # Parse tool name: plugin.command
        if '.' not in tool_name:
            return {"error": f"Invalid tool name format: {tool_name}"}
        
        plugin_name, command = tool_name.split('.', 1)
        
        if plugin_name not in plugin_registry:
            return {"error": f"Plugin not found: {plugin_name}"}
        
        cli_path = plugin_registry[plugin_name]["path"]
        
        # Build command arguments
        cmd = [sys.executable, cli_path, command]
        for key, value in arguments.items():
            cmd.extend([f"--{key}", str(value)])
        
        logger.info(f"Executing plugin command: {' '.join(cmd)}")
        
        # Execute the plugin
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        if result.returncode == 0:
            try:
                plugin_result = json.loads(result.stdout.strip())
                if "error" in plugin_result:
                    return {"error": plugin_result["error"]}
                else:
                    return {"result": plugin_result.get("result", plugin_result)}
            except json.JSONDecodeError:
                return {"result": result.stdout.strip()}
        else:
            return {"error": result.stderr.strip() or "Plugin execution failed"}
            
    except subprocess.TimeoutExpired:
        return {"error": "Plugin execution timed out"}
    except Exception as e:
        logger.error(f"Error executing plugin tool {tool_name}: {e}")
        return {"error": str(e)}


async def sse_handler(request: Request) -> StreamResponse:
    """Handle SSE connections for MCP protocol."""
    session_id = str(uuid.uuid4())
    
    # Create session
    sessions[session_id] = {
        "id": session_id,
        "created": asyncio.get_event_loop().time()
    }
    
    logger.info(f"New SSE connection established: {session_id}")
    
    # Create SSE response
    response = StreamResponse(
        status=200,
        headers={
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
    )
    
    await response.prepare(request)
    
    try:
        # Send initial connection message (simple format, not JSON-RPC)
        connection_event = {
            "type": "connection_established",
            "session_id": session_id
        }
        raw_message = f"data: {json.dumps(connection_event)}\n\n"
        logger.info(f"RAW SSE connection message: {json.dumps(connection_event)}")
        logger.info(f"RAW SSE wire format: {repr(raw_message)}")
        await response.write(raw_message.encode())
        logger.info(f"Sent connection established for session {session_id}")
        
        # Keep connection alive
        while True:
            transport = request.transport
            if transport is None or transport.is_closing():
                break
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in SSE connection {session_id}: {e}")
    finally:
        # Cleanup session
        if session_id in sessions:
            del sessions[session_id]
        logger.info(f"SSE connection closed: {session_id}")
    
    return response


async def message_handler(request: Request) -> Response:
    """Handle MCP message requests (tool invocations)."""
    logger.info(f"Message endpoint called with method: {request.method}")
    logger.info(f"Message endpoint headers: {dict(request.headers)}")
    
    try:
        body = await request.json()
        logger.info(f"Message endpoint received body: {json.dumps(body, indent=2)}")
        
        # Validate JSON-RPC 2.0 format
        if not isinstance(body, dict):
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request"
                },
                "id": None
            })
        
        jsonrpc = body.get("jsonrpc")
        request_id = body.get("id")
        method = body.get("method")
        params = body.get("params", {})
        
        if jsonrpc != "2.0":
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: jsonrpc must be '2.0'"
                },
                "id": request_id
            })
        
        if method == "initialize":
            # Handle initialization
            return web.json_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "sanctum-letta-mcp",
                        "version": "2.2.0"
                    }
                }
            })
        
        elif method == "tools/list":
            # Handle tools list request
            logger.info(f"Tools list request received for session {request_id}")
            tools = build_tools_manifest()
            logger.info(f"Returning {len(tools)} tools")
            return web.json_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tools}
            })
        
        elif method == "tools/call":
            # Handle tool invocation
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                return web.json_response({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: missing tool name"
                    },
                    "id": request_id
                })
            
            # Execute the tool
            result = await execute_plugin_tool(tool_name, arguments)
            
            if "error" in result:
                return web.json_response({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": result["error"]
                    },
                    "id": request_id
                })
            else:
                return web.json_response({
                    "jsonrpc": "2.0",
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": str(result["result"])
                            }
                        ]
                    },
                    "id": request_id
                })
        
        else:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            })
            
    except json.JSONDecodeError:
        return web.json_response({
            "jsonrpc": "2.0",
            "error": {
                "code": -32700,
                "message": "Parse error"
            },
            "id": None
        })
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        return web.json_response({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error"
            },
            "id": body.get("id") if isinstance(body, dict) else None
        })


async def health_handler(request: Request) -> Response:
    """Health check endpoint."""
    return web.json_response({
        "status": "healthy",
        "plugins": len(plugin_registry),
        "sessions": len(sessions)
    })


async def init_app() -> web.Application:
    """Initialize the aiohttp application."""
    global plugin_registry
    
    logger.info("Starting Sanctum Letta MCP Server...")
    
    # Discover plugins
    plugin_registry = discover_plugins()
    logger.info(f"Discovered {len(plugin_registry)} plugins")
    
    # Create application
    app = web.Application()
    
    # Setup CORS
    cors = cors_setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Add routes
    app.router.add_get('/mcp/sse', sse_handler)
    app.router.add_post('/mcp/message', message_handler)
    app.router.add_get('/health', health_handler)
    
    # Apply CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    logger.info("Server startup complete")
    return app


def main():
    """Main entry point."""
    port = int(os.getenv("MCP_PORT", "8000"))
    host = os.getenv("MCP_HOST", "0.0.0.0")
    
    logger.info(f"Starting MCP server on {host}:{port}")
    
    app = asyncio.run(init_app())
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    main() 