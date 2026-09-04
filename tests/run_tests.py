"""
Standalone test runner using standard library to test all AgentPay invariants, Multi-Agent Squad roles, and Multi-Merchant flows.
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from agentpay.database.models import (
    Base,
    AgentPolicy,
    Transaction,
    PaymentIntent,
    Receipt,
    AuditEvent,
    TransactionStatus,
    ActorType
)
from agentpay.database.seed import seed_database
from agentpay.policy.engine import PolicyEngine
from agentpay.transactions.state_machine import TransactionStateMachine, InvalidStateTransitionError
from agentpay.transactions.service import TransactionService
from agentpay.merchants.service import MerchantService
from agentpay.agents.buyer import AIBuyer, SAFE_TOOLS_SCHEMA
from agentpay.agents.intent import IntentAgent


def get_test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    seed_database(db)
    return db


def run_all_tests():
    passed = 0
    failed = 0

    print("=" * 60)
    print("RUNNING AGENTPAY TEST SUITE")
    print("=" * 60)

    # 1. Test Policy Approval
    try:
        db = get_test_db()
        res = PolicyEngine.evaluate("agent_001", 4499.0, "audio", "merchant_001", db)
        assert res.approved is True, "Expected approved for ₹4,499"
        assert res.code == "POLICY_APPROVED"
        print(" [PASS] test_policy_approval_under_limit")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_policy_approval_under_limit: {e}")
        failed += 1

    # 2. Test Policy Limit Denial
    try:
        db = get_test_db()
        res = PolicyEngine.evaluate("agent_001", 85000.0, "electronics", "merchant_001", db)
        assert res.approved is False, "Expected denied for ₹85,000"
        assert res.code == "TRANSACTION_LIMIT_EXCEEDED"
        print(" [PASS] test_policy_denial_exceeding_limit")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_policy_denial_exceeding_limit: {e}")
        failed += 1

    # 3. Test Policy Category Denial
    try:
        db = get_test_db()
        res = PolicyEngine.evaluate("agent_001", 1200.0, "luxury_jewelry", "merchant_001", db)
        assert res.approved is False
        assert res.code == "CATEGORY_NOT_ALLOWED"
        print(" [PASS] test_policy_denial_unauthorized_category")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_policy_denial_unauthorized_category: {e}")
        failed += 1

    # 4. Test State Machine Transitions & Audit Log
    try:
        db = get_test_db()
        tx = Transaction(id="tx_test_01", purchase_intent_id="pi_01", status="CREATED")
        db.add(tx)
        db.commit()

        TransactionStateMachine.transition(tx, "POLICY_CHECKED", "POLICY_ENGINE", "POLICY_STARTED", {}, db)
        assert tx.status == "POLICY_CHECKED"

        TransactionStateMachine.transition(tx, "APPROVED", "POLICY_ENGINE", "POLICY_APPROVED", {}, db)
        assert tx.status == "APPROVED"

        events = db.query(AuditEvent).filter(AuditEvent.transaction_id == "tx_test_01").all()
        assert len(events) == 2
        print(" [PASS] test_state_machine_valid_transitions")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_state_machine_valid_transitions: {e}")
        failed += 1

    # 5. Test State Machine Denied Terminal Behavior
    try:
        db = get_test_db()
        tx = Transaction(id="tx_test_02", purchase_intent_id="pi_02", status="POLICY_CHECKED")
        db.add(tx)
        db.commit()

        TransactionStateMachine.transition(tx, "DENIED", "POLICY_ENGINE", "DENIED", {}, db)
        assert tx.status == "DENIED"

        # Subsequent transition should fail
        has_raised = False
        try:
            TransactionStateMachine.transition(tx, "PAYMENT_CREATED", "PAYMENT_SERVICE", "PAY", {}, db)
        except InvalidStateTransitionError:
            has_raised = True
        assert has_raised, "Transition from DENIED should raise InvalidStateTransitionError"
        print(" [PASS] test_state_machine_denied_is_terminal")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_state_machine_denied_is_terminal: {e}")
        failed += 1

    # 6. Test Scenario 1: Positive Approved Headphones
    try:
        db = get_test_db()
        result = TransactionService.create_and_process_intent(
            agent_id="agent_001",
            merchant_id="merchant_001",
            product_id="prod_jbl_770nc",
            amount=4499.0,
            currency="INR",
            db=db
        )
        assert result["status"] == "RECEIPT_GENERATED"
        assert result["receipt"] is not None
        assert result["receipt"]["amount"] == 4499.0

        events = db.query(AuditEvent).filter(AuditEvent.transaction_id == result["id"]).all()
        assert len(events) == 9
        event_types = [e.event_type for e in events]
        assert "BUDGET_RESERVED" in event_types
        assert "BUDGET_COMMITTED" in event_types
        print(" [PASS] test_scenario_1_positive_approved_headphones (9 audit events verified with reserve-commit)")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_scenario_1_positive_approved_headphones: {e}")
        failed += 1

    # 7. Test Scenario 2: Negative Denied Laptop (The Core Proof Point)
    try:
        db = get_test_db()
        result = TransactionService.create_and_process_intent(
            agent_id="agent_001",
            merchant_id="merchant_001",
            product_id="prod_dell_xps15",
            amount=85000.0,
            currency="INR",
            db=db
        )
        assert result["status"] == "DENIED"
        assert result["policy_result"]["approved"] is False
        assert result["policy_result"]["code"] == "TRANSACTION_LIMIT_EXCEEDED"

        # Verify Payment Service was NEVER called
        payments = db.query(PaymentIntent).filter(PaymentIntent.purchase_intent_id == result["purchase_intent"]["id"]).all()
        assert len(payments) == 0, "No payment intent should exist for denied transaction"
        print(" [PASS] test_scenario_2_negative_denied_laptop (payment rail untouched)")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_scenario_2_negative_denied_laptop: {e}")
        failed += 1

    # 8. Test Security Boundary (AI Buyer cannot call money-moving tools)
    try:
        db = get_test_db()
        buyer = AIBuyer(agent_id="agent_001")
        for bad_tool in ["charge_card", "transfer_money", "modify_policy", "modify_limits", "access_payment_credentials"]:
            res = buyer.execute_tool(bad_tool, {}, db)
            assert res.get("error") == "SECURITY_VIOLATION"
        print(" [PASS] test_security_boundary_forbidden_tools")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_security_boundary_forbidden_tools: {e}")
        failed += 1

    # 9. Test Rolling 24h Daily Limit Enforcement
    try:
        db = get_test_db()
        policy = db.query(AgentPolicy).filter(AgentPolicy.agent_id == "agent_001").first()
        policy.per_transaction_limit = 5000.0
        policy.daily_spending_limit = 8000.0
        db.commit()

        # First transaction of ₹4,499 -> approved
        res1 = TransactionService.create_and_process_intent(
            agent_id="agent_001",
            merchant_id="merchant_001",
            product_id="prod_jbl_770nc",
            amount=4499.0,
            db=db
        )
        assert res1["status"] == "RECEIPT_GENERATED"

        # Second transaction of ₹4,000 -> daily limit exceeded
        eval_res = PolicyEngine.evaluate("agent_001", 4000.0, "accessories", "merchant_001", db)
        assert eval_res.approved is False
        assert eval_res.code == "DAILY_LIMIT_EXCEEDED"
        print(" [PASS] test_policy_denial_daily_limit_exceeded (rolling velocity protection)")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_policy_denial_daily_limit_exceeded: {e}")
        failed += 1

    # 10. Test Webhook Signature Verification
    try:
        from apps.api.routes.webhooks import verify_razorpay_signature
        import hmac
        import hashlib

        secret = "test_webhook_secret_key"
        payload_bytes = b'{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_123"}}}}'
        valid_sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

        assert verify_razorpay_signature(payload_bytes, valid_sig, secret) is True
        assert verify_razorpay_signature(payload_bytes, "invalid_sig", secret) is False
        print(" [PASS] test_razorpay_webhook_signature_verification")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_razorpay_webhook_signature_verification: {e}")
        failed += 1

    # 11. Test IntentAgent Constraint & Parameter Parsing
    try:
        parsed = IntentAgent.parse_intent("Buy a Sony 4K monitor with USB-C under ₹30,000")
        assert parsed["brand"] == "Sony"
        assert parsed["category"] == "displays"
        assert parsed["max_price"] == 30000.0
        assert "4k" in parsed["feature_keywords"]
        assert "usb-c" in parsed["feature_keywords"]
        assert parsed["is_buy_command"] is True
        print(" [PASS] test_intent_agent_constraint_parsing")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_intent_agent_constraint_parsing: {e}")
        failed += 1

    # 12. Test Single Agent: search_products Tool Execution
    try:
        db = get_test_db()
        buyer = AIBuyer(agent_id="agent_001")
        search_args = {
            "query": "headphones anc",
            "category": "audio",
            "max_price": 5000.0,
            "feature_keywords": ["anc"]
        }
        search_res = buyer.execute_tool("search_products", search_args, db)
        products = search_res.get("products", [])
        assert len(products) >= 2
        merchant_ids = {p["merchant_id"] for p in products}
        assert len(merchant_ids) >= 2, "Should discover products across multiple merchants"
        print(" [PASS] test_single_agent_tool_search_products")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_single_agent_tool_search_products: {e}")
        failed += 1

    # 13. Test Single Agent: get_quote Tool Execution & Comparison
    try:
        db = get_test_db()
        buyer = AIBuyer(agent_id="agent_001")
        # Direct quote resolution for candidate product
        quote_res = buyer.execute_tool("get_quote", {"product_id": "prod_jbl_770nc"}, db)
        assert quote_res.get("quote") is not None
        assert quote_res["quote"]["total_amount"] == 4499.0
        assert quote_res["quote"]["product_id"] == "prod_jbl_770nc"
        print(" [PASS] test_single_agent_tool_get_quote")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_single_agent_tool_get_quote: {e}")
        failed += 1

    # 14. Test Single Agent: create_purchase_intent Tool Execution
    try:
        db = get_test_db()
        buyer = AIBuyer(agent_id="agent_001")
        intent_args = {
            "product_id": "prod_jbl_770nc",
            "amount": 4499.0,
            "idempotency_key": "test_idempotency_intent_001"
        }
        intent_res = buyer.execute_tool("create_purchase_intent", intent_args, db)
        assert intent_res.get("transaction") is not None
        assert intent_res["transaction"]["status"] == "RECEIPT_GENERATED"
        print(" [PASS] test_single_agent_tool_create_purchase_intent")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_single_agent_tool_create_purchase_intent: {e}")
        failed += 1

    # 15. Test Single Agent Multi-Tool Calling Autonomous Execution Pipeline
    try:
        db = get_test_db()
        buyer = AIBuyer(agent_id="agent_001")
        agent_res = buyer.chat("Auto-buy wireless headphones with active noise cancellation under ₹5,000", db)
        assert agent_res["transaction"] is not None
        assert agent_res["transaction"]["status"] == "RECEIPT_GENERATED"

        # Verify multiple tool calls executed by the single agent
        tool_calls = [s["tool"] for s in agent_res["steps"] if s["step"] == "TOOL_CALL"]
        assert "search_products" in tool_calls, "Single Agent must call search_products"
        assert "get_quote" in tool_calls, "Single Agent must call get_quote"
        assert "create_purchase_intent" in tool_calls, "Single Agent must call create_purchase_intent"
        assert "get_receipt" in tool_calls, "Single Agent must call get_receipt"

        # Verify AgentPay Gateway evaluation step
        gateway_steps = [s for s in agent_res["steps"] if s["step"] == "GATEWAY_EVALUATION"]
        assert len(gateway_steps) > 0, "AgentPay Gateway authorization must be evaluated"

        print(" [PASS] test_single_agent_multi_tool_calling_pipeline (search -> quote -> intent -> receipt)")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_single_agent_multi_tool_calling_pipeline: {e}")
        failed += 1

    # 16. Test Human-in-the-Loop Clarification & Choice Loop
    try:
        db = get_test_db()
        buyer = AIBuyer(agent_id="agent_001")
        broad_res = buyer.chat("Show headphones", db)
        assert broad_res["clarification"] is not None
        assert "clarifying_question" in broad_res["clarification"] or "question" in broad_res["clarification"]
        assert len(broad_res["clarification"]["options"]) > 0
        assert broad_res["transaction"] is None  # Ensures zero premature debit
        print(" [PASS] test_hitl_clarification_loop (interactive questions & options verified)")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_hitl_clarification_loop: {e}")
        failed += 1

    # 17. Test Graceful Failure Reserve-Then-Release Flow
    try:
        db = get_test_db()
        init_budget = PolicyEngine.get_budget_summary("agent_001", db)
        fail_res = TransactionService.create_and_process_intent(
            agent_id="agent_001",
            merchant_id="merchant_001",
            product_id="prod_keychron_k2",
            amount=4999.0,
            currency="INR",
            simulate_failure=True,
            db=db
        )
        assert fail_res["status"] == "PAYMENT_FAILED"
        payment = db.query(PaymentIntent).filter(PaymentIntent.purchase_intent_id == fail_res["purchase_intent"]["id"]).first()
        assert payment is not None
        assert payment.status == "RELEASED"

        events = db.query(AuditEvent).filter(AuditEvent.transaction_id == fail_res["id"]).all()
        ev_types = [e.event_type for e in events]
        assert "BUDGET_RESERVED" in ev_types
        assert "BUDGET_RELEASED" in ev_types

        # Verify budget restored
        restored_budget = PolicyEngine.get_budget_summary("agent_001", db)
        assert restored_budget["currently_reserved"] == 0.0
        assert restored_budget["available_budget"] == init_budget["available_budget"]
        print(" [PASS] test_graceful_failure_reserve_then_release (budget restored, 0 leaked funds)")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_graceful_failure_reserve_then_release: {e}")
        failed += 1

    # 18. Test Explicit Two-Phase Atomic Reserve Then Commit & Release
    try:
        from test_purchase_intent_flow import test_two_phase_atomic_reserve_then_commit_and_release
        db = get_test_db()
        test_two_phase_atomic_reserve_then_commit_and_release(db)
        print(" [PASS] test_two_phase_atomic_reserve_then_commit_and_release (PaymentIntent: AUTHORIZED -> CAPTURED/RELEASED)")
        passed += 1
    except Exception as e:
        print(f" [FAIL] test_two_phase_atomic_reserve_then_commit_and_release: {e}")
        failed += 1

    print("=" * 60)
    print(f"TEST RESULTS: {passed} PASSED, {failed} FAILED")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
