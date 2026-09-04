"""
Tests for Agent-Readable Catalog & Protocol Specifications.
Verifies compliance with:
1. /.well-known/agent-catalog.json (ACP/UAP Schema, Razorpay settlement rails)
2. /.well-known/uap-manifest.json (NPCI UAP Network draft)
3. /.well-known/ai-plugin.json (Standard AI Plugin spec)
4. /llms.txt (LLM text grounding catalog feed)
5. /api/v1/protocol/x402/checkout (HTTP 402 Payment Required Challenge & Headers)
"""
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_agent_readable_catalog_manifest(client):
    """Verify /.well-known/agent-catalog.json conforms to Agent Commerce Protocol."""
    resp = client.get("/.well-known/agent-catalog.json")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()

    assert data.get("gateway") == "AgentPay"
    assert "ACP" in data.get("protocol", "") or "UAP" in data.get("protocol", "")
    assert "settlement_rail" in data
    assert data["settlement_rail"]["provider"] == "RAZORPAY"
    assert data["settlement_rail"]["currency"] == "INR"
    assert "upi" in data["settlement_rail"]["supported_methods"]

    # Verify policy governance rules are exposed to agents
    assert "policy_governance" in data
    assert "per_transaction_limit" in data["policy_governance"]["enforced_checks"]

    # Verify products are exposed in schema.org format
    products = data.get("products", [])
    assert len(products) > 0, "Expected catalog products to be present"
    first = products[0]
    assert first["@type"] == "Product"
    assert "sku" in first
    assert "offers" in first
    assert first["offers"]["priceCurrency"] == "INR"
    assert first["offers"]["pricePaise"] > 0
    assert first["offers"]["quote_ttl_seconds"] == 300


def test_uap_network_manifest(client):
    """Verify /.well-known/uap-manifest.json conforms to NPCI UAP specifications."""
    resp = client.get("/.well-known/uap-manifest.json")
    assert resp.status_code == 200
    data = resp.json()

    assert data["participant_id"] == "gateway.agentpay.in"
    assert data["role"] == "AGENT_COMMERCE_GATEWAY"
    assert data["settlement"]["rail"] == "RAZORPAY_TEST_MODE"
    assert "UAP-2026" in data["supported_protocols"]
    assert "x402 (Payment Required Rail)" in data["supported_protocols"]
    assert data["invariants"]["zero_unauthorized_draws"] is True
    assert data["invariants"]["atomic_rollback_on_failure"] is True


def test_ai_plugin_manifest(client):
    """Verify /.well-known/ai-plugin.json for OpenAI/Agent discovery."""
    resp = client.get("/.well-known/ai-plugin.json")
    assert resp.status_code == 200
    data = resp.json()

    assert data["schema_version"] == "v1"
    assert data["name_for_model"] == "agentpay_commerce"
    assert data["auth"]["type"] == "none"
    assert "api" in data


def test_llms_txt_feed(client):
    """Verify /llms.txt returns clean plaintext markdown for crawler agents."""
    resp = client.get("/llms.txt")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    content = resp.text

    assert "# AgentPay Verified Merchant Catalog" in content
    assert "Two-Phase Reserve-Then-Commit" in content
    assert "Verified Merchants" in content
    assert "Available Catalog Products" in content
    assert "**SKU**:" in content
    assert "₹" in content


def test_x402_payment_required_challenge(client):
    """Verify /api/v1/protocol/x402/checkout returns HTTP 402 with Razorpay headers."""
    resp = client.post(
        "/api/v1/protocol/x402/checkout",
        json={"product_id": "prod_001", "agent_id": "agent_001"}
    )
    # The HTTP Status MUST be 402 Payment Required!
    assert resp.status_code == 402, f"Expected 402 Payment Required, got {resp.status_code}"

    # Verify standard protocol headers
    assert resp.headers.get("X-Payment-Rail") == "razorpay"
    assert "x402" in resp.headers.get("X-Payment-Protocol", "")
    assert "order_x402_" in resp.headers.get("X-Razorpay-Order-Id", "")
    assert int(resp.headers.get("X-Amount-Paise", 0)) > 0
    assert "WWW-Authenticate" in resp.headers
    assert "X402" in resp.headers.get("WWW-Authenticate", "")

    # Verify body payload for agent resolution
    body = resp.json()
    assert body["status"] == 402
    assert body["title"] == "Payment Required"
    assert "payment_challenge" in body
    assert body["payment_challenge"]["rail"] == "RAZORPAY"
    assert body["payment_challenge"]["network"] == "test"
    assert body["resolution_instructions"]["action"] == "create_purchase_intent"
    assert body["resolution_instructions"]["endpoint"] == "/api/v1/purchase-intents"


def test_x402_payment_authorized_flow(client):
    """Verify /api/v1/protocol/x402/checkout clears order when AgentPay token is supplied."""
    resp = client.post(
        "/api/v1/protocol/x402/checkout",
        json={"product_id": "prod_001", "agent_id": "agent_001"},
        headers={"Authorization": "AgentPay token_verified_by_policy_engine"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == 200
    assert body["protocol"] == "x402-settled"
    assert "cleared for fulfillment" in body["message"].lower()
