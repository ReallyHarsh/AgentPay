import pytest
from agentpay.database.models import get_db, SessionLocal
from agentpay.agents.buyer import AIBuyer
from agentpay.agents.graph import (
    agentpay_graph_app,
    evaluate_retrieval_node,
    rewrite_query_node,
    AgentPayGraphState
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_langgraph_direct_mouse_retrieval(db):
    """
    Verify that querying 'buy a mouse' in LangGraph:
    1. Directs straight to retrieve -> evaluate -> propose (NO clarification)
    2. Proposes a mouse (Logitech MX Master 3S or Logitech Lift)
    3. Guarantees tiered options are mice only (no keyboards or power banks)
    """
    buyer = AIBuyer("agent_001")
    result = buyer.chat("buy a mouse", db)

    # 1. No clarification
    assert result["clarification"] is None
    assert result["proposal"] is not None

    # 2. Top recommendation is a mouse
    proposal = result["proposal"]
    assert "mouse" in proposal["name"].lower() or proposal["sub_type"] == "mouse"

    # 3. Steps include LangGraph nodes
    step_tools = [s.get("tool") for s in result["steps"]]
    assert "langgraph_parse_intent" in step_tools
    assert "search_products" in step_tools
    assert "get_quote" in step_tools

    # 4. Tiered options must be mice only
    for opt in proposal.get("tiered_options", []):
        assert "mouse" in opt["name"].lower()


def test_langgraph_clarification_branch(db):
    """
    Verify that querying a broad category like 'Show accessories' triggers
    the clarify node and stops execution before charging or proposing.
    """
    buyer = AIBuyer("agent_001")
    result = buyer.chat("Show accessories", db)

    assert result["clarification"] is not None
    assert "question" in result["clarification"]
    assert len(result["clarification"]["options"]) > 0
    assert result["transaction"] is None
    assert result["proposal"] is None

    step_tools = [s.get("tool") for s in result["steps"]]
    assert "langgraph_parse_intent" in step_tools
    assert "request_clarification" in step_tools


def test_langgraph_corrective_rag_node():
    """
    Verify that evaluate_retrieval_node flags a mismatch when target sub_type
    does not match the retrieved top product, and rewrite_query_node refines it.
    """
    mock_state: AgentPayGraphState = {
        "intent_data": {
            "sub_type": "mouse",
            "clean_query": "ergonomic device"
        },
        "products": [
            {"id": "prod_cam", "name": "Logitech 4K Webcam", "sub_type": "webcam", "price": 14995.0}
        ],
        "retry_count": 0,
        "steps": []
    }

    eval_result = evaluate_retrieval_node(mock_state)
    assert eval_result["needs_rewrite"] is True

    # Now run rewrite_query_node
    mock_state["needs_rewrite"] = True
    rewrite_result = rewrite_query_node(mock_state)
    assert rewrite_result["retry_count"] == 1
    assert "mouse" in rewrite_result["intent_data"]["clean_query"]


def test_langgraph_autonomous_checkout(db):
    """
    Verify that an autonomous purchase command executes all LangGraph tool calls
    including search_products, get_quote, create_purchase_intent, and get_receipt.
    """
    buyer = AIBuyer("agent_001")
    result = buyer.chat("Auto-buy wireless headphones with active noise cancellation under ₹5,000", db)

    assert result["transaction"] is not None
    assert result["transaction"]["status"] == "RECEIPT_GENERATED"

    tool_calls = [s["tool"] for s in result["steps"] if s["step"] == "TOOL_CALL"]
    assert "search_products" in tool_calls
    assert "get_quote" in tool_calls
    assert "create_purchase_intent" in tool_calls
    assert "get_receipt" in tool_calls

    gateway_steps = [s for s in result["steps"] if s["step"] == "GATEWAY_EVALUATION"]
    assert len(gateway_steps) > 0
