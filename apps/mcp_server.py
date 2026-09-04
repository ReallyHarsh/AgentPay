"""
AgentPay Standalone Model Context Protocol (MCP) Server Entrypoint.
Enables AI Agents (Claude Desktop, Cursor, Antigravity, custom agents)
to interact with AgentPay commerce rails via stdio or SSE transport.

Usage:
  # Stdio transport (default for Claude Desktop / Cursor / Antigravity):
  python -m apps.mcp_server

  # SSE transport for network-accessible agents:
  python -m apps.mcp_server --transport sse --port 8001
"""
import sys
import os
import argparse

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agentpay.mcp.server import get_mcp_server


def main():
    parser = argparse.ArgumentParser(description="AgentPay Model Context Protocol (MCP) Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port for SSE transport (default: 8001)"
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default="agent_001",
        help="Agent identity for policy rails (default: agent_001)"
    )
    args = parser.parse_args()

    server = get_mcp_server(agent_id=args.agent_id)

    if args.transport == "stdio":
        # Stdio transport for Claude Desktop / Cursor / Antigravity
        server.run(transport="stdio")
    elif args.transport == "sse":
        # SSE transport
        server.run(transport="sse", port=args.port)


if __name__ == "__main__":
    main()
