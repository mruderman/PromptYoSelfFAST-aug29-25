#!/usr/bin/env python3
"""
Sanctum Letta MCP Server

A Server-Sent Events (SSE) server for orchestrating plugin execution using aiohttp.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from aiohttp import web, ClientSession
from aiohttp.web import Request, Response, StreamResponse
from aiohttp_cors import setup as cors_setup, ResourceOptions, CorsViewMixin


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

# Plugin registry and help cache
plugin_registry: Dict[str, Dict[str, Any]] = {}
help_cache: Dict[str, Any] = {}


def discover_plugins() -> Dict[str, Dict[str, Any]]:
    """Discover available plugins by scanning the plugins directory."""
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


def get_plugin_help(plugin_name: str) -> Optional[Dict[str, Any]]:
    """Get help information for a plugin."""
    if plugin_name not in plugin_registry:
        return None
    
    try:
        cli_path = plugin_registry[plugin_name]["path"]
        result = subprocess.run(
            [sys.executable, cli_path, "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return {
                "help": result.stdout,
                "commands": plugin_registry[plugin_name]["commands"]
            }
        else:
            logger.error(f"Failed to get help for plugin {plugin_name}: {result.stderr}")
            return None
    except Exception as e:
        logger.error(f"Error getting help for plugin {plugin_name}: {e}")
        return None


def build_help_cache() -> Dict[str, Any]:
    """Build the help cache for all plugins."""
    cache = {}
    
    for plugin_name in plugin_registry:
        help_info = get_plugin_help(plugin_name)
        if help_info:
            cache[plugin_name] = help_info
    
    return cache


async def execute_plugin(plugin_name: str, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a plugin command."""
    if plugin_name not in plugin_registry:
        return {"error": f"Plugin not found: {plugin_name}"}
    
    try:
        cli_path = plugin_registry[plugin_name]["path"]
        
        # Build command arguments
        cmd = [sys.executable, cli_path, action]
        for key, value in args.items():
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
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {"result": result.stdout.strip()}
        else:
            return {"error": result.stderr.strip() or "Plugin execution failed"}
            
    except subprocess.TimeoutExpired:
        return {"error": "Plugin execution timed out"}
    except Exception as e:
        logger.error(f"Error executing plugin {plugin_name}: {e}")
        return {"error": str(e)}


async def health_handler(request: Request) -> Response:
    """Health check endpoint."""
    return web.json_response({
        "status": "healthy", 
        "plugins": len(plugin_registry)
    })


async def help_handler(request: Request) -> Response:
    """Get help information for all plugins."""
    return web.json_response(help_cache)


async def reload_help_handler(request: Request) -> Response:
    """Reload the help cache."""
    global help_cache
    help_cache = build_help_cache()
    logger.info("Help cache reloaded")
    return web.json_response({
        "status": "ok", 
        "message": "Help cache reloaded"
    })


async def run_plugin_handler(request: Request) -> StreamResponse:
    """Execute a plugin command with SSE response streaming."""
    try:
        body = await request.json()
        plugin_name = body.get("plugin")
        action = body.get("action")
        args = body.get("args", {})
        
        if not plugin_name or not action:
            return web.json_response({
                "error": "Missing required fields: plugin and action"
            })
        
        # Create SSE response
        response = StreamResponse(
            status=200,
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )
        
        await response.prepare(request)
        
        # Send queued status
        await response.write(f"data: {json.dumps({'status': 'queued', 'payload': {}})}\n\n".encode())
        
        # Send started status
        await response.write(f"data: {json.dumps({'status': 'started', 'payload': {}})}\n\n".encode())
        
        # Execute plugin
        result = await execute_plugin(plugin_name, action, args)
        
        # Send final status
        if "error" in result:
            await response.write(f"data: {json.dumps({'status': 'error', 'payload': result})}\n\n".encode())
        else:
            await response.write(f"data: {json.dumps({'status': 'success', 'payload': result})}\n\n".encode())
        
        return response
        
    except Exception as e:
        logger.error(f"Error in run_plugin: {e}")
        return web.json_response({"error": str(e)})


async def init_app() -> web.Application:
    """Initialize the aiohttp application."""
    global plugin_registry, help_cache
    
    logger.info("Starting Sanctum Letta MCP Server...")
    
    # Discover plugins
    plugin_registry = discover_plugins()
    logger.info(f"Discovered {len(plugin_registry)} plugins")
    
    # Build help cache
    help_cache = build_help_cache()
    logger.info("Help cache built successfully")
    
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
    app.router.add_get('/health', health_handler)
    app.router.add_get('/help', help_handler)
    app.router.add_post('/reload-help', reload_help_handler)
    app.router.add_post('/run', run_plugin_handler)
    
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