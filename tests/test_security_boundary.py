from agentpay.agents.buyer import AIBuyer, SAFE_TOOLS_SCHEMA


def test_ai_buyer_tool_boundary(db_session):
    buyer = AIBuyer(agent_id="agent_001")

    # Verify only safe tools are exposed in schema
    exposed_tool_names = [t["function"]["name"] for t in SAFE_TOOLS_SCHEMA]
    assert set(exposed_tool_names) == {
        "search_products",
        "get_quote",
        "create_purchase_intent",
        "get_transaction_status",
        "get_receipt"
    }

    # Verify dangerous money-moving tools are never exposed
    forbidden_tools = [
        "charge_card",
        "transfer_money",
        "modify_policy",
        "modify_limits",
        "access_payment_credentials",
        "direct_debit"
    ]
    for forbidden in forbidden_tools:
        assert forbidden not in exposed_tool_names

        # Attempting execution directly must return a SECURITY_VIOLATION error
        res = buyer.execute_tool(forbidden, {}, db_session)
        assert res.get("error") == "SECURITY_VIOLATION"
