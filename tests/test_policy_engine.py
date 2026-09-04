from agentpay.policy.engine import PolicyEngine
from agentpay.database.models import AgentPolicy


def test_policy_approval_under_limit(db_session):
    result = PolicyEngine.evaluate(
        agent_id="agent_001",
        amount=4499.0,
        category="audio",
        merchant_id="merchant_001",
        db=db_session
    )
    assert result.approved is True
    assert result.code == "POLICY_APPROVED"
    assert result.requested_amount == 4499.0


def test_policy_denial_exceeding_limit(db_session):
    result = PolicyEngine.evaluate(
        agent_id="agent_001",
        amount=85000.0,
        category="electronics",
        merchant_id="merchant_001",
        db=db_session
    )
    assert result.approved is False
    assert result.code == "TRANSACTION_LIMIT_EXCEEDED"
    assert "exceeds agent per-transaction limit" in result.reason


def test_policy_denial_unauthorized_category(db_session):
    result = PolicyEngine.evaluate(
        agent_id="agent_001",
        amount=1200.0,
        category="luxury_jewelry",
        merchant_id="merchant_001",
        db=db_session
    )
    assert result.approved is False
    assert result.code == "CATEGORY_NOT_ALLOWED"


def test_policy_denial_blocked_merchant(db_session):
    # Block a merchant
    policy = db_session.query(AgentPolicy).filter(AgentPolicy.agent_id == "agent_001").first()
    policy.blocked_merchants = ["blocked_merchant_999"]
    db_session.commit()

    result = PolicyEngine.evaluate(
        agent_id="agent_001",
        amount=500.0,
        category="electronics",
        merchant_id="blocked_merchant_999",
        db=db_session
    )
    assert result.approved is False
    assert result.code == "MERCHANT_BLOCKED"
