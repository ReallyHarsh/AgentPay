"""
Model Context Protocol (MCP) API Routes.
Exposes standardized MCP tool schemas, server capabilities manifest,
and direct tool calling endpoints compliant with the Anthropic Model Context Protocol specification.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
from agentpay.mcp.server import get_mcp_server, get_mcp_tools_list, FORBIDDEN_TOOLS

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP)"])


class MCPToolCallRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Key-value arguments for the tool")
    agent_id: Optional[str] = Field(default="agent_001", description="Agent ID submitting the request")


@router.get("/manifest", summary="Retrieve MCP Server Capabilities Manifest")
async def get_mcp_manifest():
    """
    Returns AgentPay MCP server metadata, protocol version, and policy security invariants.
    """
    return {
        "name": "AgentPay-MCP-Server",
        "version": "1.0.0",
        "protocol_version": "2024-11-05",
        "description": "Standardized Model Context Protocol (MCP) tool provider for autonomous AI commerce and policy-supervised payments.",
        "provider": "Razorpay AgentPay Initiative",
        "capabilities": {
            "tools": {
                "listChanged": False
            },
            "resources": {},
            "prompts": {}
        },
        "security_invariants": {
            "financial_rails_isolation": "AI agents formulate intents only; policy engine and Razorpay rails enforce limits.",
            "forbidden_tools": list(FORBIDDEN_TOOLS),
            "two_phase_lifecycle": "reserve-then-commit (AUTHORIZED -> CAPTURED/RELEASED)"
        }
    }


@router.get("/tools", summary="List All Standardized MCP Tools")
async def list_mcp_tools(agent_id: str = "agent_001"):
    """
    Returns all tools exposed by the AgentPay MCP Server formatted according
    to the Model Context Protocol specification (with inputSchema, titles, and descriptions).
    """
    tools = await get_mcp_tools_list(agent_id=agent_id)
    return {
        "tools": tools,
        "total_tools": len(tools)
    }


@router.post("/tools/{tool_name}/call", summary="Execute an MCP Tool")
async def call_mcp_tool(tool_name: str, payload: MCPToolCallRequest):
    """
    Directly invokes an MCP tool using the standardized Model Context Protocol execution engine.
    """
    if tool_name in FORBIDDEN_TOOLS:
        raise HTTPException(
            status_code=403,
            detail=f"Security Violation: Tool '{tool_name}' is a forbidden financial rails tool."
        )

    server = get_mcp_server(agent_id=payload.agent_id or "agent_001")
    
    try:
        res = await server.call_tool(tool_name, payload.arguments)
        
        # Parse text content
        output_text = res.content[0].text if res.content else ""
        parsed_result = None
        try:
            parsed_result = json.loads(output_text)
        except Exception:
            parsed_result = output_text

        return {
            "tool": tool_name,
            "is_error": res.is_error,
            "content": [c.model_dump() if hasattr(c, "model_dump") else str(c) for c in res.content],
            "result": parsed_result
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error executing MCP tool '{tool_name}': {str(e)}"
        )
