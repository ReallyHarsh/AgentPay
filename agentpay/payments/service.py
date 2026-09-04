import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from agentpay.database.models import PaymentIntent, PurchaseIntent, PaymentIntentStatus
from agentpay.payments.razorpay import RazorpayAdapter


class PaymentService:
    """
    Two-Phase Reserve-Then-Commit Payment Service.
    1. reserve_payment: Locks budget immediately on policy approval (RESERVED)
    2. commit_payment: Permanently captures payment upon Razorpay confirmation (COMMITTED / PAYMENT_SUCCESS)
    3. release_payment: Voids reservation and restores budget upon decline/failure (RELEASED / PAYMENT_FAILED)
    """

    def __init__(self, adapter: RazorpayAdapter = None):
        self.adapter = adapter or RazorpayAdapter()

    def reserve_payment(
        self,
        purchase_intent: PurchaseIntent,
        db: Session
    ) -> PaymentIntent:
        """
        Phase 1: Reserve funds against the agent's available daily budget
        immediately upon policy approval, before Razorpay payment execution completes.
        """
        # Check if already reserved
        existing = db.query(PaymentIntent).filter(PaymentIntent.purchase_intent_id == purchase_intent.id).first()
        if existing:
            existing.status = PaymentIntentStatus.AUTHORIZED.value
            existing.reserved_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            return existing

        payment_intent = PaymentIntent(
            id=f"pay_int_{uuid.uuid4().hex[:12]}",
            purchase_intent_id=purchase_intent.id,
            provider="RAZORPAY",
            provider_payment_id=None,
            amount=purchase_intent.amount,
            currency=purchase_intent.currency,
            status=PaymentIntentStatus.AUTHORIZED.value,
            reserved_at=datetime.now(timezone.utc)
        )
        db.add(payment_intent)
        db.commit()
        db.refresh(payment_intent)
        return payment_intent

    def commit_payment(
        self,
        payment_intent: PaymentIntent,
        provider_payment_id: str,
        db: Session
    ) -> PaymentIntent:
        """
        Phase 2A (Success): Permanently commit reserved budget upon verified Razorpay capture.
        """
        payment_intent.status = PaymentIntentStatus.CAPTURED.value
        payment_intent.provider_payment_id = provider_payment_id
        payment_intent.committed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(payment_intent)
        return payment_intent

    def release_payment(
        self,
        payment_intent: PaymentIntent,
        db: Session,
        reason: str = "PAYMENT_FAILED"
    ) -> PaymentIntent:
        """
        Phase 2B (Failure/Rollback): Immediately release and void the reservation,
        restoring the locked amount back into the agent's available daily budget.
        """
        payment_intent.status = PaymentIntentStatus.RELEASED.value
        payment_intent.released_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(payment_intent)
        return payment_intent

    def process_payment_for_intent(
        self,
        purchase_intent: PurchaseIntent,
        db: Session,
        simulate_failure: bool = False,
        simulate_timeout: bool = False
    ) -> PaymentIntent:
        """
        Executes full two-phase reserve-then-commit workflow.
        Attaches enterprise order notes: agent_id, purchase_intent_id, policy_id.
        """
        # 1. Reserve funds immediately
        payment_intent = self.reserve_payment(purchase_intent, db)

        # Resolve policy_id for reconciliation in Razorpay Dashboard
        policy_id = "policy_001"
        if purchase_intent.agent and hasattr(purchase_intent.agent, "policy") and purchase_intent.agent.policy:
            policy_id = purchase_intent.agent.policy.id

        order_notes = {
            "agent_id": purchase_intent.agent_id,
            "purchase_intent_id": purchase_intent.id,
            "policy_id": policy_id,
            "product_id": purchase_intent.product_id,
            "merchant_id": getattr(purchase_intent, "merchant_id", "merchant_001"),
            "idempotency_key": getattr(purchase_intent, "idempotency_key", None),
            "gateway": "AgentPay-v1.1",
            "simulate_failure": simulate_failure
        }

        # 2. Call Razorpay adapter
        result = self.adapter.create_payment(
            amount=purchase_intent.amount,
            currency=purchase_intent.currency,
            receipt=f"rcpt_pi_{purchase_intent.id[:8]}",
            notes=order_notes,
            simulate_failure=simulate_failure,
            simulate_timeout=simulate_timeout
        )

        status = result.get("status")

        # 3. Commit, Hold on Timeout, or Release reservation
        if status == "PAYMENT_SUCCESS":
            payment_intent = self.commit_payment(
                payment_intent=payment_intent,
                provider_payment_id=result.get("provider_payment_id"),
                db=db
            )
        elif status == "NETWORK_TIMEOUT":
            # Timeout during payment dispatch: reservation remains in AUTHORIZED hold for idempotent retry
            payment_intent.status = PaymentIntentStatus.AUTHORIZED.value
            db.commit()
            db.refresh(payment_intent)
        else:
            payment_intent = self.release_payment(
                payment_intent=payment_intent,
                db=db,
                reason=result.get("error", {}).get("description", "Payment Declined")
            )

        return payment_intent
