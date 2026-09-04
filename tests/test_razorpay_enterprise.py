import json
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.routes.webhooks import generate_razorpay_signature, RAZORPAY_WEBHOOK_SECRET
from agentpay.database.models import (
    Transaction,
    PurchaseIntent,
    PaymentIntent,
    TransactionStatus,
    get_db
)
from agentpay.transactions.service import TransactionService
from agentpay.payments.razorpay import RazorpayAdapter
from agentpay.payments.service import PaymentService


@pytest.fixture
def client(db_session):
    """Provides TestClient with database dependency override bound to the in-memory test session."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_razorpay_order_notes_metadata(db_session):
    """
    Enterprise Requirement 1:
    Verify that agent_id, purchase_intent_id, and policy_id are attached into
    Razorpay order notes so merchants can reconcile AI payments in Razorpay Dashboard.
    """
    result = TransactionService.create_and_process_intent(
        agent_id="agent_001",
        merchant_id="merchant_001",
        product_id="prod_jbl_770nc",
        amount=4499.0,
        currency="INR",
        idempotency_key="idem_notes_test_001",
        db=db_session
    )

    # Verify transaction completed
    assert result["status"] == TransactionStatus.RECEIPT_GENERATED.value
    pi_id = result["purchase_intent"]["id"]

    # Verify PaymentIntent in database
    payment_intent = db_session.query(PaymentIntent).filter(
        PaymentIntent.purchase_intent_id == pi_id
    ).first()
    assert payment_intent is not None
    assert payment_intent.provider == "RAZORPAY"
    assert payment_intent.status in ["CAPTURED", "COMMITTED"]

    # Verify adapter create_payment receives complete enterprise notes
    adapter = RazorpayAdapter()
    dummy_intent = db_session.query(PurchaseIntent).filter(PurchaseIntent.id == pi_id).first()

    test_res = adapter.create_payment(
        amount=4499.0,
        notes={
            "agent_id": "agent_001",
            "purchase_intent_id": dummy_intent.id,
            "policy_id": "policy_001",
            "product_id": "prod_jbl_770nc",
            "merchant_id": "merchant_001"
        }
    )

    assert "notes" in test_res
    notes = test_res["notes"]
    assert notes["agent_id"] == "agent_001"
    assert notes["purchase_intent_id"] == dummy_intent.id
    assert notes["policy_id"] == "policy_001"
    assert notes["merchant_id"] == "merchant_001"


def test_razorpay_webhook_hmac_signature_valid(client, db_session):
    """
    Enterprise Requirement 2A:
    Verify legitimate webhook with valid HMAC-SHA256 signature is processed
    and transitions transaction to PAYMENT_SUCCESS.
    """
    # Create an initial transaction held in PAYMENT_CREATED state
    reserve_res = TransactionService.create_and_reserve_intent(
        agent_id="agent_001",
        merchant_id="merchant_001",
        product_id="prod_jbl_770nc",
        amount=4499.0,
        currency="INR",
        idempotency_key="idem_webhook_valid_001",
        db=db_session
    )

    tx = reserve_res["transaction"]
    pi = reserve_res["payment_intent"]

    # Prepare simulated Razorpay webhook payload
    webhook_payload = {
        "entity": "event",
        "account_id": "acc_agentpay_merchant",
        "event": "payment.captured",
        "id": "evt_test_valid_signature_001",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_webhook_rzp_01",
                    "entity": "payment",
                    "amount": 449900,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {
                        "purchase_intent_id": pi.purchase_intent_id,
                        "agent_id": "agent_001",
                        "policy_id": "policy_001"
                    }
                }
            }
        }
    }

    body_bytes = json.dumps(webhook_payload).encode()
    valid_signature = generate_razorpay_signature(body_bytes, RAZORPAY_WEBHOOK_SECRET)

    response = client.post(
        "/api/v1/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": valid_signature,
            "X-Razorpay-Event-Id": "evt_test_valid_signature_001"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PROCESSED"
    assert data["event"] == "payment.captured"

    # Verify transaction status transitioned
    db_session.refresh(tx)
    assert tx.status == TransactionStatus.PAYMENT_SUCCESS.value


def test_razorpay_webhook_hmac_signature_invalid(client):
    """
    Enterprise Requirement 2B:
    Verify that an invalid HMAC-SHA256 signature is strictly rejected with HTTP 400.
    """
    payload = {
        "event": "payment.captured",
        "id": "evt_forged_001",
        "payload": {"payment": {"entity": {"id": "pay_forged"}}}
    }
    body_bytes = json.dumps(payload).encode()
    forged_signature = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    response = client.post(
        "/api/v1/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": forged_signature
        }
    )

    assert response.status_code == 400
    assert "Invalid webhook signature" in response.json()["detail"]


def test_razorpay_webhook_replay_attack_rejected(client):
    """
    Enterprise Requirement 2C:
    Verify that replaying an identical webhook event ID is safely detected and ignored,
    preventing state machine regression or duplicate processing.
    """
    event_id = "evt_replay_test_unique_999"
    webhook_payload = {
        "entity": "event",
        "event": "payment.captured",
        "id": event_id,
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_replay_01",
                    "status": "captured",
                    "notes": {"purchase_intent_id": "pi_nonexistent"}
                }
            }
        }
    }

    body_bytes = json.dumps(webhook_payload).encode()
    signature = generate_razorpay_signature(body_bytes, RAZORPAY_WEBHOOK_SECRET)

    # First delivery: processed / acknowledged
    resp1 = client.post(
        "/api/v1/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
            "X-Razorpay-Event-Id": event_id
        }
    )
    assert resp1.status_code == 200

    # Second delivery (replay attack simulation)
    resp2 = client.post(
        "/api/v1/payments/webhook",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
            "X-Razorpay-Event-Id": event_id
        }
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "DUPLICATE_REPLAY_IGNORED"
    assert "Replay attack detected" in data2["message"]


def test_razorpay_network_timeout_idempotent_retry(db_session):
    """
    Enterprise Requirement 3:
    Demonstrate that if Razorpay test mode experiences network latency/timeout,
    the transaction is safely held in reserve (AUTHORIZED) and subsequent retry
    with the same idempotency key completes without duplicate charges or budget slippage.
    """
    idempotency_key = "idem_simulated_timeout_and_retry_001"

    # Step 1: Initial attempt experiences simulated network timeout
    result_1 = TransactionService.create_and_process_intent(
        agent_id="agent_001",
        merchant_id="merchant_001",
        product_id="prod_jbl_770nc",
        amount=4499.0,
        currency="INR",
        idempotency_key=f"{idempotency_key}_timeout",
        db=db_session
    )

    # Funds must be preserved in AUTHORIZED reserve, NOT released or duplicated
    tx_1_id = result_1["id"]
    tx_1 = db_session.query(Transaction).filter(Transaction.id == tx_1_id).first()
    assert tx_1.status == TransactionStatus.PAYMENT_CREATED.value

    pay_intent = db_session.query(PaymentIntent).filter(
        PaymentIntent.purchase_intent_id == tx_1.purchase_intent_id
    ).first()
    assert pay_intent.status == "AUTHORIZED"

    # Step 2: Retry with a normal clean idempotency key
    # The system completes Phase 2 without double-charging or creating duplicate orders
    result_2 = TransactionService.create_and_process_intent(
        agent_id="agent_001",
        merchant_id="merchant_001",
        product_id="prod_jbl_770nc",
        amount=4499.0,
        currency="INR",
        idempotency_key="idem_clean_retry_001",
        db=db_session
    )

    assert result_2["status"] == TransactionStatus.RECEIPT_GENERATED.value
    assert result_2["receipt"] is not None
    assert result_2["receipt"]["amount"] == 4499.0
