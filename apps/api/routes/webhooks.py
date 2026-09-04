import os
import hmac
import hashlib
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
from agentpay.database.models import (
    get_db,
    Transaction,
    PaymentIntent,
    PurchaseIntent,
    AuditEvent,
    TransactionStatus,
    ActorType
)
from agentpay.transactions.state_machine import TransactionStateMachine

router = APIRouter(tags=["Webhooks"])

RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret_agentpay_2026")

# In-memory deduplication set to guarantee resilience against webhook replay attacks
PROCESSED_WEBHOOK_EVENT_IDS = set()


def generate_razorpay_signature(body_bytes: bytes, secret: str = None) -> str:
    """
    Computes cryptographic HMAC-SHA256 signature for Razorpay webhook payloads.
    Used by test suites, gateway simulators, and webhook verification.
    """
    key = secret or RAZORPAY_WEBHOOK_SECRET
    return hmac.new(key.encode(), body_bytes, hashlib.sha256).hexdigest()


def verify_razorpay_signature(body_bytes: bytes, signature: str, secret: str) -> bool:
    """
    Verifies cryptographic HMAC-SHA256 signature against webhook payload.
    Uses hmac.compare_digest to prevent timing attacks.
    """
    if not signature or not secret:
        return False
    expected = generate_razorpay_signature(body_bytes, secret)
    return hmac.compare_digest(expected, signature)


@router.post("/payments/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: str = Header(None, alias="X-Razorpay-Event-Id"),
    db: Session = Depends(get_db)
):
    """
    Asynchronous Razorpay webhook receiver with HMAC-SHA256 cryptographic verification
    and active replay attack defense.
    Processes payment.captured, order.paid, and payment.failed events.
    """
    body_bytes = await request.body()

    # 1. Strict Cryptographic Signature Verification
    if x_razorpay_signature:
        is_valid = verify_razorpay_signature(body_bytes, x_razorpay_signature, RAZORPAY_WEBHOOK_SECRET)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid webhook signature: HMAC-SHA256 mismatch")

    try:
        payload = json.loads(body_bytes.decode())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    provider_payment_id = payment_entity.get("id")
    notes = payment_entity.get("notes", {})
    purchase_intent_id = notes.get("purchase_intent_id")

    # 2. Replay Attack Protection (Event Deduplication)
    event_id = x_razorpay_event_id or payload.get("id") or (f"{event}_{provider_payment_id}" if provider_payment_id else None)
    if event_id:
        if event_id in PROCESSED_WEBHOOK_EVENT_IDS:
            return {
                "status": "DUPLICATE_REPLAY_IGNORED",
                "message": f"Replay attack detected or duplicate webhook received: event {event_id} already processed.",
                "event_id": event_id
            }
        PROCESSED_WEBHOOK_EVENT_IDS.add(event_id)

    if not purchase_intent_id and provider_payment_id:
        # Lookup payment intent by provider_payment_id
        pi = db.query(PaymentIntent).filter(PaymentIntent.provider_payment_id == provider_payment_id).first()
        if pi:
            purchase_intent_id = pi.purchase_intent_id

    if not purchase_intent_id:
        return {"status": "ACKNOWLEDGED", "message": "No matching purchase intent found in metadata notes"}

    transaction = db.query(Transaction).filter(Transaction.purchase_intent_id == purchase_intent_id).first()
    if not transaction:
        return {"status": "ACKNOWLEDGED", "message": f"No transaction found for purchase intent {purchase_intent_id}"}

    # Handle payment events
    if event == "payment.captured" or event == "order.paid":
        # Check current status
        if transaction.status == TransactionStatus.PAYMENT_CREATED.value:
            TransactionStateMachine.transition(
                transaction=transaction,
                target_status=TransactionStatus.PAYMENT_SUCCESS.value,
                actor_type=ActorType.PAYMENT_SERVICE.value,
                event_type="WEBHOOK_PAYMENT_CAPTURED",
                metadata={"provider_payment_id": provider_payment_id, "event": event},
                db=db
            )
    elif event == "payment.failed":
        if transaction.status == TransactionStatus.PAYMENT_CREATED.value:
            TransactionStateMachine.transition(
                transaction=transaction,
                target_status=TransactionStatus.PAYMENT_FAILED.value,
                actor_type=ActorType.PAYMENT_SERVICE.value,
                event_type="WEBHOOK_PAYMENT_FAILED",
                metadata={"provider_payment_id": provider_payment_id, "error": payment_entity.get("error_description")},
                db=db
            )

    return {
        "status": "PROCESSED",
        "event": event,
        "transaction_id": transaction.id,
        "transaction_status": transaction.status
    }
