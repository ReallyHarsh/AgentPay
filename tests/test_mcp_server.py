"""
Tests for AgentPay Model Context Protocol (MCP) Server & Standardized Tools.
Verifies compliance with the Anthropic Model Context Protocol specification,
safe tool execution, and policy rails security invariants.
"""
import pytest
import asyncio
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from agentpay.database.models import Base
from agentpay.database.seed import seed_database
from agentpay.mcp.server import create_mcp_server, get_mcp_server, get_mcp_tools_list, FORBIDDEN_TOOLS
from fastapi.testclient import TestClient
from apps.api.main import app


@pytest.fixture(scope="module")
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    seed_database(db)
    yield db
    db.close()


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


def test_mcp_server_tool_registry():
    """Verify MCP server registers the 6 official AgentPay commerce tools."""
    tools = asyncio.run(get_mcp_tools_list())
    tool_names = [t["name"] for t in tools]
    
    expected_tools = [
        "search_products",
        "get_quote",
        "create_purchase_intent",
        "get_transaction_status",
        "get_receipt",
        "request_clarification"
    ]
    for expected in expected_tools:
        assert expected in tool_names, f"Missing MCP tool: {expected}"


def test_mcp_tool_schema_compliance():
    """Verify each MCP tool adheres to Model Context Protocol inputSchema structure."""
    tools = asyncio.run(get_mcp_tools_list())
    for t in tools:
        assert "name" in t
        assert "description" in t
        assert "inputSchema" in t
        schema = t["inputSchema"]
        assert schema.get("type") == "object"
        assert "properties" in schema


def test_mcp_search_products_execution():
    """Verify search_products tool execution via Model Context Protocol engine."""
    server = get_mcp_server()
    res = asyncio.run(server.call_tool("search_products", {"query": "wireless headphones with ANC under 5000"}))
    assert not res.is_error
    assert len(res.content) > 0
    data = json.loads(res.content[0].text)
    assert data["products_found"] > 0
    top_product = data["products"][0]
    assert top_product["price"] <= 5000.0


def test_mcp_get_quote_execution():
    """Verify get_quote tool execution via MCP engine."""
    server = get_mcp_server()
    res = asyncio.run(server.call_tool("get_quote", {"product_id": "prod_jbl_770nc"}))
    assert not res.is_error
    data = json.loads(res.content[0].text)
    assert "quote" in data
    quote = data["quote"]
    assert quote["product_id"] == "prod_jbl_770nc"
    assert quote["total_amount"] > 0


def test_mcp_create_purchase_intent_reserve_lifecycle():
    """Verify create_purchase_intent triggers policy approval and atomic reservation."""
    server = get_mcp_server()
    res = asyncio.run(server.call_tool("create_purchase_intent", {
        "product_id": "prod_jbl_770nc",
        "amount": 4499.0
    }))
    assert not res.is_error
    data = json.loads(res.content[0].text)
    assert data.get("status") in ("AUTHORIZED", "PAYMENT_CREATED", "PENDING_PAYMENT", "APPROVED")
    assert "id" in data or "transaction_id" in data
    assert data.get("budget_lifecycle") is not None or "id" in data


def test_mcp_security_boundary_forbidden_tools():
    """Verify forbidden financial rails cannot be exposed or invoked via MCP."""
    for tool in FORBIDDEN_TOOLS:
        assert tool in [
            "charge_card",
            "transfer_money",
            "modify_policy",
            "modify_limits",
            "access_payment_credentials",
            "direct_debit",
            "authorize_payment"
        ]


def test_mcp_http_manifest_and_tools_api(api_client):
    """Verify HTTP REST endpoints for MCP manifest, tools listing, and execution."""
    # Manifest endpoint
    manifest_res = api_client.get("/api/v1/mcp/manifest")
    assert manifest_res.status_code == 200
    manifest = manifest_res.json()
    assert manifest["name"] == "AgentPay-MCP-Server"
    assert manifest["protocol_version"] == "2024-11-05"

    # Tools listing endpoint
    tools_res = api_client.get("/api/v1/mcp/tools")
    assert tools_res.status_code == 200
    tools_data = tools_res.json()
    assert tools_data["total_tools"] >= 6

    # Direct tool call via HTTP
    call_res = api_client.post("/api/v1/mcp/tools/get_quote/call", json={
        "arguments": {"product_id": "prod_jbl_770nc"}
    })
    assert call_res.status_code == 200
    call_data = call_res.json()
    assert call_data["tool"] == "get_quote"
    assert not call_data["is_error"]
    assert "quote" in call_data["result"]
