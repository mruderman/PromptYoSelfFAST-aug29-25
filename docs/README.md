# Sanctum Letta MCP Documentation

Welcome to the documentation for the **Sanctum Letta MCP (SSE Edition)** - a powerful, modular orchestration server designed to securely expose and manage command-line tools and automation scripts within your internal infrastructure. Built for the Letta Agentic AI framework, this MCP operates as a **Server-Sent Events (SSE) server** using aiohttp for real-time communication and is fully compliant with the Model Context Protocol (MCP).

## Overview
The Sanctum Letta MCP is a production-ready, SSE-based server that provides:
- **Real-time communication** via Server-Sent Events over HTTP
- **Dynamic plugin discovery** - auto-discovers all plugins in `mcp/plugins/` at startup
- **BotFather automation** - Telegram BotFather operations (click buttons, send messages)
- **DevOps automation** - Application deployment, rollback, and status management
- **Comprehensive testing** - Full test suite with coverage reporting and timeout protection
- **Single worker thread** - Serializes all plugin execution for safety

## Key Features
- **SSE Server:** Real-time communication via Server-Sent Events over HTTP using aiohttp
- **Dynamic Plugin Architecture:** Plugins are auto-discovered at startup; no code changes needed
- **BotFather Integration:** Click buttons and send messages to BotFather
- **DevOps Automation:** Deploy, rollback, and check application status
- **Comprehensive Testing:** Full test suite with coverage reporting and timeout protection
- **Production-Ready:** Designed for container deployment with Letta
- **Sanctum Stack Compatible:** Uses aiohttp, pydantic, and other Sanctum-standard libraries

## Documentation Structure
- [Getting Started](getting-started.md) - Installation and basic usage (SSE)
- [API Reference](api-reference.md) - SSE message protocol and HTTP endpoints
- [Contract Analysis](mcp-contract-analysis.md) - MCP compliance and protocol details
- [Monitoring](monitoring.md) - Health checks, logging, and troubleshooting
- [Plugin Development](plugin-development.md) - Guide for creating plugins
- [Security](security.md) - Security best practices and session management
- [Testing Guide](testing.md) - Comprehensive testing documentation

## Quick Links
- [Source Code](https://github.com/actuallyrizzn/sanctum-letta-mcp)
- [Changelog](../CHANGELOG.md)
- [Main README](../README.md)

## Docker Deployment
This MCP server is designed to work with self-hosted Letta/Sanctum servers running in Docker containers. See the [Getting Started](getting-started.md) guide for Docker networking configuration.

---
For any questions or contributions, please refer to the [Security](security.md) and [Plugin Development](plugin-development.md) guides. 