from agentpay.transactions.service import TransactionService
from agentpay.database.models import Transaction, PaymentIntent, Receipt, AuditEvent
from agentpay.policy.engine import PolicyEngine


def test_positive_approved_scenario_headphones(db_session):
    """
    Scenario 1: Approved Purchase Flow with Reserve-Then-Commit
    - Product: JBL Tune 770NC (₹4,499)
    - Policy Limit: ₹5,000
    - Outcome: APPROVED -> BUDGET_RESERVED -> PAYMENT_SUCCESS -> BUDGET_COMMITTED -> ORDER_CONFIRMED -> RECEIPT_GENERATED
    - Full audit trail verified with two-phase commit
    """
    result = TransactionService.create_and_process_intent(
        agent_id="agent_001",
        merchant_id="merchant_001",
        product_id="prod_jbl_770nc",
        amount=4499.0,
        currency="INR",
        db=db_session
    )

    tx_id = result["id"]
    assert result["status"] == "RECEIPT_GENERATED"
    assert result["receipt"] is not None
    assert result["receipt"]["amount"] == 4499.0

    # Verify payment intent was created and committed
    payment = db_session.query(PaymentIntent).filter(PaymentIntent.purchase_intent_id == result["purchase_intent"]["id"]).first()
    assert payment is not None
    assert payment.status in ["CAPTURED", "COMMITTED", "PAYMENT_SUCCESS"]
    assert payment.amount == 4499.0
    assert payment.committed_at is not None

    # Verify receipt generated
    receipt = db_session.query(Receipt).filter(Receipt.transaction_id == tx_id).first()
    assert receipt is not None
    assert receipt.receipt_number.startswith("RCPT-")

    # Verify audit log events appended (including BUDGET_RESERVED and BUDGET_COMMITTED)
    audit_events = db_session.query(AuditEvent).filter(AuditEvent.transaction_id == tx_id).all()
    assert len(audit_events) == 9
    event_types = [e.event_type for e in audit_events]
    assert "PURCHASE_INTENT_CREATED" in event_types
    assert "POLICY_EVALUATION_STARTED" in event_types
    assert "POLICY_EVALUATION_APPROVED" in event_types
    assert "BUDGET_RESERVED" in event_types
    assert "PAYMENT_AUTHORIZATION_INITIATED" in event_types
    assert "BUDGET_COMMITTED" in event_types
    assert "PAYMENT_CAPTURED_SUCCESSFULLY" in event_types
    assert "MERCHANT_ORDER_CONFIRMED" in event_types
    assert "RECEIPT_ISSUED" in event_types


def test_negative_denied_scenario_laptop(db_session):
    """
    Scenario 2: Denied Purchase Flow (Core Proof Point)
    - Product: Dell XPS 15 (₹85,000)
    - Policy Limit: ₹5,000
    - Outcome: DENIED (TRANSACTION_LIMIT_EXCEEDED)
    - Proof: Payment service is NEVER called, no PaymentIntent exists, zero budget reserved
    """
    result = TransactionService.create_and_process_intent(
        agent_id="agent_001",
        merchant_id="merchant_001",
        product_id="prod_dell_xps15",
        amount=85000.0,
        currency="INR",
        db=db_session
    )

    tx_id = result["id"]
    assert result["status"] == "DENIED"
    assert result["policy_result"]["approved"] is False
    assert result["policy_result"]["code"] == "TRANSACTION_LIMIT_EXCEEDED"
    assert result["receipt"] is None

    # CRITICAL: Verify Payment Service was NEVER called
    payment_intents = db_session.query(PaymentIntent).filter(PaymentIntent.purchase_intent_id == result["purchase_intent"]["id"]).all()
    assert len(payment_intents) == 0

    # Verify receipts were NEVER generated
    receipts = db_session.query(Receipt).filter(Receipt.transaction_id == tx_id).all()
    assert len(receipts) == 0

    # Verify audit trail stops at denial
    audit_events = db_session.query(AuditEvent).filter(AuditEvent.transaction_id == tx_id).all()
    event_types = [e.event_type for e in audit_events]
    assert "PURCHASE_INTENT_CREATED" in event_types
    assert "POLICY_EVALUATION_DENIED" in event_types
    assert "BUDGET_RESERVED" not in event_types
    assert "PAYMENT_AUTHORIZATION_INITIATED" not in event_types


def test_graceful_payment_failure_reserve_then_release(db_session):
    """
    Scenario 3: Graceful Failure Reserve-Then-Release Flow
    - Product: Keychron K2 Keyboard (₹4,999)
    - Policy Limit: ₹5,000
    - Policy Check: APPROVED -> ₹4,999 immediately RESERVED
    - Gateway Rail: Bank payment declines (Simulated Card Decline)
    - Outcome: PAYMENT_FAILED -> Reservation immediately RELEASED
    - Proof: Available budget is 100% restored, zero leaked money, audit trail records RELEASE
    """
    initial_budget = PolicyEngine.get_budget_summary("agent_001", db_session)

    result = TransactionService.create_and_process_intent(
        agent_id="agent_001",
        merchant_id="merchant_001",
        product_id="prod_keychron_k2",
        amount=4999.0,
        currency="INR",
        simulate_failure=True,
        db=db_session
    )

    tx_id = result["id"]
    assert result["status"] == "PAYMENT_FAILED"
    assert result["receipt"] is None

    # Payment intent was created and then RELEASED
    payment = db_session.query(PaymentIntent).filter(PaymentIntent.purchase_intent_id == result["purchase_intent"]["id"]).first()
    assert payment is not None
    assert payment.status == "RELEASED"
    assert payment.released_at is not None

    # Verify audit trail records both reserve and release
    audit_events = db_session.query(AuditEvent).filter(AuditEvent.transaction_id == tx_id).all()
    event_types = [e.event_type for e in audit_events]
    assert "PURCHASE_INTENT_CREATED" in event_types
    assert "POLICY_EVALUATION_APPROVED" in event_types
    assert "BUDGET_RESERVED" in event_types
    assert "BUDGET_RELEASED" in event_types
    assert "PAYMENT_AUTHORIZATION_FAILED" in event_types

    # Verify available budget is completely restored (no money leaked)
    final_budget = PolicyEngine.get_budget_summary("agent_001", db_session)
    assert final_budget["currently_reserved"] == 0.0
    assert final_budget["spent_today"] == initial_budget["spent_today"]
    assert final_budget["available_budget"] == initial_budget["available_budget"]


def test_two_phase_atomic_reserve_then_commit_and_release(db_session):
    """
    Scenario 4: Explicit Two-Phase Reserve-Then-Commit Isolation
    Proves that:
    1. Phase 1 create_and_reserve_intent sets PaymentIntent: AUTHORIZED and
       immediately drops available budget while raising currently_reserved BEFORE payment execution.
    2. Phase 2 finalize_payment with decline sets PaymentIntent: RELEASED and
       instantly restores available budget back up.
    3. Phase 2 finalize_payment with success sets PaymentIntent: CAPTURED and
       commits funds to 24h spend.
    """
    # Baseline budget
    b0 = PolicyEngine.get_budget_summary("agent_001", db_session)

    # --- TEST 1: Reserve -> Release Flow ---
    # Phase 1: Reserve only
    reserve_res = TransactionService.create_and_reserve_intent(
        agent_id="agent_001",
        merchant_id="merchant_001",
        product_id="prod_keychron_k2",
        amount=4999.0,
        currency="INR",
        db=db_session
    )
    tx = reserve_res["transaction"]
    pi = reserve_res["payment_intent"]
    assert tx.status == "PAYMENT_CREATED"
    assert pi.status in ("AUTHORIZED", "RESERVED")
    assert pi.reserved_at is not None

    # Verify visible budget consequence at Phase 1: hold is active, available budget has dropped!
    b1 = PolicyEngine.get_budget_summary("agent_001", db_session)
    assert b1["currently_reserved"] == 4999.0
    assert b1["available_budget"] == b0["available_budget"] - 4999.0

    # Phase 2: Finalize with failure (Decline card)
    finalize_res = TransactionService.finalize_payment(
        transaction=tx,
        payment_intent=pi,
        simulate_failure=True,
        db=db_session
    )
    assert finalize_res["status"] == "PAYMENT_FAILED"
    assert pi.status == "RELEASED"
    assert pi.released_at is not None

    # Verify visible budget consequence after release: available budget is restored back UP!
    b2 = PolicyEngine.get_budget_summary("agent_001", db_session)
    assert b2["currently_reserved"] == 0.0
    assert b2["available_budget"] == b0["available_budget"]

    # --- TEST 2: Reserve -> Commit Flow ---
    reserve_res_success = TransactionService.create_and_reserve_intent(
        agent_id="agent_001",
        merchant_id="merchant_001",
        product_id="prod_jbl_770nc",
        amount=4499.0,
        currency="INR",
        db=db_session
    )
    tx_s = reserve_res_success["transaction"]
    pi_s = reserve_res_success["payment_intent"]
    assert pi_s.status in ("AUTHORIZED", "RESERVED")

    # Phase 2: Finalize with success
    commit_res = TransactionService.finalize_payment(
        transaction=tx_s,
        payment_intent=pi_s,
        simulate_failure=False,
        db=db_session
    )
    assert commit_res["status"] == "RECEIPT_GENERATED"
    assert pi_s.status in ("CAPTURED", "COMMITTED")
    assert pi_s.committed_at is not None

    b3 = PolicyEngine.get_budget_summary("agent_001", db_session)
    assert b3["currently_reserved"] == 0.0
    assert b3["spent_today"] == b0["spent_today"] + 4499.0

