import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from agentpay.database.models import (
    Transaction,
    PurchaseIntent,
    PaymentIntent,
    Product,
    Merchant,
    AuditEvent,
    TransactionStatus,
    ActorType
)
from agentpay.policy.engine import PolicyEngine
from agentpay.transactions.state_machine import TransactionStateMachine
from agentpay.payments.service import PaymentService
from agentpay.merchants.service import MerchantService
from agentpay.receipts.service import ReceiptService


class TransactionService:
    @staticmethod
    def create_and_reserve_intent(
        agent_id: str,
        merchant_id: str,
        product_id: str,
        amount: float,
        currency: str = "INR",
        idempotency_key: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Phase 1 (Reserve): Evaluates policy. If approved, immediately creates PaymentIntent
        with status AUTHORIZED (Razorpay literal) and locks the amount against available budget.
        If denied, transitions to DENIED (terminal). Zero funds are reserved.
        """
        # 1. Check Idempotency Key
        if idempotency_key:
            existing_pi = db.query(PurchaseIntent).filter(PurchaseIntent.idempotency_key == idempotency_key).first()
            if existing_pi and existing_pi.transaction:
                return {
                    "transaction": existing_pi.transaction,
                    "payment_intent": existing_pi.payment_intent,
                    "policy_result": None,
                    "formatted": TransactionService.format_transaction_response(existing_pi.transaction, db)
                }

        # 2. Validate product & merchant
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product {product_id} not found in catalog")

        product_category = product.category
        pre_reserve_budget = PolicyEngine.get_budget_summary(agent_id, db)

        # Create unique IDs
        pi_id = f"pi_{uuid.uuid4().hex[:12]}"
        tx_id = f"tx_{uuid.uuid4().hex[:12]}"

        # 3. Create PurchaseIntent Record
        purchase_intent = PurchaseIntent(
            id=pi_id,
            agent_id=agent_id,
            merchant_id=merchant_id,
            product_id=product_id,
            amount=amount,
            currency=currency,
            status=TransactionStatus.CREATED.value,
            idempotency_key=idempotency_key
        )
        db.add(purchase_intent)

        # 4. Create Transaction Record (State: CREATED)
        transaction = Transaction(
            id=tx_id,
            purchase_intent_id=pi_id,
            status=TransactionStatus.CREATED.value
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        # Audit Event 1: Intent Created
        audit_1 = AuditEvent(
            id=f"audit_{uuid.uuid4().hex[:12]}",
            transaction_id=tx_id,
            event_type="PURCHASE_INTENT_CREATED",
            actor_type=ActorType.AI_BUYER.value
        )
        audit_1.event_metadata = {
            "product_id": product_id,
            "product_name": product.name,
            "category": product_category,
            "amount": amount,
            "currency": currency,
            "merchant_id": merchant_id
        }
        db.add(audit_1)
        db.commit()

        # 5. Evaluate Policy Engine
        TransactionStateMachine.transition(
            transaction=transaction,
            target_status=TransactionStatus.POLICY_CHECKED.value,
            actor_type=ActorType.POLICY_ENGINE.value,
            event_type="POLICY_EVALUATION_STARTED",
            metadata={"agent_id": agent_id, "amount": amount, "category": product_category},
            db=db
        )

        policy_result = PolicyEngine.evaluate(
            agent_id=agent_id,
            amount=amount,
            category=product_category,
            merchant_id=merchant_id,
            db=db
        )

        if not policy_result.approved:
            # Policy DENIED -> Terminal State
            TransactionStateMachine.transition(
                transaction=transaction,
                target_status=TransactionStatus.DENIED.value,
                actor_type=ActorType.POLICY_ENGINE.value,
                event_type="POLICY_EVALUATION_DENIED",
                metadata=policy_result.to_dict(),
                db=db
            )
            purchase_intent.status = TransactionStatus.DENIED.value
            db.add(purchase_intent)
            db.commit()

            return {
                "transaction": transaction,
                "payment_intent": None,
                "policy_result": policy_result,
                "pre_reserve_budget": pre_reserve_budget,
                "budget_reserve_snapshot": pre_reserve_budget,
                "formatted": TransactionService.format_transaction_response(transaction, db, policy_result)
            }

        # Policy APPROVED: Immediately Reserve Funds (Phase 1)
        TransactionStateMachine.transition(
            transaction=transaction,
            target_status=TransactionStatus.APPROVED.value,
            actor_type=ActorType.POLICY_ENGINE.value,
            event_type="POLICY_EVALUATION_APPROVED",
            metadata=policy_result.to_dict(),
            db=db
        )
        purchase_intent.status = TransactionStatus.APPROVED.value
        db.add(purchase_intent)
        db.commit()

        # PHASE 1: Reserve PaymentIntent & lock funds against available daily limit
        # Status: AUTHORIZED (Razorpay literal)
        payment_service = PaymentService()
        payment_intent = payment_service.reserve_payment(purchase_intent, db)
        transaction.payment_intent_id = payment_intent.id
        db.add(transaction)
        db.commit()

        budget_reserve_snapshot = PolicyEngine.get_budget_summary(agent_id, db)

        # Record Audit Event: Budget Reserved
        audit_reserve = AuditEvent(
            id=f"audit_{uuid.uuid4().hex[:12]}",
            transaction_id=tx_id,
            event_type="BUDGET_RESERVED",
            actor_type=ActorType.POLICY_ENGINE.value
        )
        audit_reserve.event_metadata = {
            "reserved_amount": amount,
            "currency": currency,
            "payment_intent_id": payment_intent.id,
            "daily_spending_limit": budget_reserve_snapshot["daily_spending_limit"],
            "spent_today": budget_reserve_snapshot["spent_today"],
            "currently_reserved": budget_reserve_snapshot["currently_reserved"],
            "available_budget": budget_reserve_snapshot["available_budget"],
            "lifecycle_stage": "AUTHORIZED",
            "note": "Amount immediately locked from available budget prior to gateway execution (PaymentIntent: AUTHORIZED)"
        }
        db.add(audit_reserve)
        db.commit()

        # Transition to PAYMENT_CREATED
        TransactionStateMachine.transition(
            transaction=transaction,
            target_status=TransactionStatus.PAYMENT_CREATED.value,
            actor_type=ActorType.PAYMENT_SERVICE.value,
            event_type="PAYMENT_AUTHORIZATION_INITIATED",
            metadata={
                "provider": "RAZORPAY",
                "amount": amount,
                "currency": currency,
                "payment_intent_id": payment_intent.id,
                "lifecycle_stage": "AUTHORIZED",
                "reserved_amount": amount,
                "available_budget": budget_reserve_snapshot["available_budget"]
            },
            db=db
        )

        return {
            "transaction": transaction,
            "payment_intent": payment_intent,
            "policy_result": policy_result,
            "pre_reserve_budget": pre_reserve_budget,
            "budget_reserve_snapshot": budget_reserve_snapshot,
            "formatted": TransactionService.format_transaction_response(transaction, db, policy_result)
        }

    @staticmethod
    def finalize_payment(
        transaction: Transaction,
        payment_intent: PaymentIntent,
        db: Session,
        simulate_failure: bool = False,
        idempotency_key: Optional[str] = None,
        policy_result: Optional[Any] = None,
        pre_reserve_budget: Optional[Dict[str, Any]] = None,
        budget_reserve_snapshot: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Phase 2: Executes the payment call against Razorpay rails.
        - On Success: COMMITS funds (PaymentIntent: CAPTURED), confirms order, issues receipt.
        - On Failure: RELEASES funds (PaymentIntent: RELEASED), voids hold, restores available budget.
        """
        payment_service = PaymentService()
        purchase_intent = transaction.purchase_intent
        agent_id = purchase_intent.agent_id
        amount = purchase_intent.amount
        currency = purchase_intent.currency
        product_id = purchase_intent.product_id
        tx_id = transaction.id

        # Check for simulated failure or timeout trigger
        should_fail = simulate_failure or bool(idempotency_key and "fail" in idempotency_key.lower())
        should_timeout = bool(idempotency_key and "timeout" in idempotency_key.lower())

        # Resolve policy_id for reconciliation in Razorpay Dashboard
        policy_id = "policy_001"
        if policy_result and hasattr(policy_result, "policy_id") and policy_result.policy_id:
            policy_id = policy_result.policy_id
        elif purchase_intent.agent and hasattr(purchase_intent.agent, "policy") and purchase_intent.agent.policy:
            policy_id = purchase_intent.agent.policy.id

        order_notes = {
            "purchase_intent_id": purchase_intent.id,
            "agent_id": purchase_intent.agent_id,
            "policy_id": policy_id,
            "product_id": purchase_intent.product_id,
            "merchant_id": getattr(purchase_intent, "merchant_id", "merchant_001"),
            "transaction_id": tx_id,
            "idempotency_key": idempotency_key,
            "gateway": "AgentPay-v1.1",
            "simulate_failure": should_fail,
            "simulate_timeout": should_timeout
        }

        # Execute Razorpay Call
        rzp_res = payment_service.adapter.create_payment(
            amount=purchase_intent.amount,
            currency=purchase_intent.currency,
            receipt=f"rcpt_pi_{purchase_intent.id[:8]}",
            notes=order_notes,
            simulate_failure=should_fail,
            simulate_timeout=should_timeout
        )

        if rzp_res.get("status") == "NETWORK_TIMEOUT":
            # Network Timeout Handling: Retain funds in AUTHORIZED reserve, do not double-debit or release
            audit_timeout = AuditEvent(
                id=f"audit_{uuid.uuid4().hex[:12]}",
                transaction_id=tx_id,
                event_type="PAYMENT_GATEWAY_TIMEOUT",
                actor_type=ActorType.PAYMENT_SERVICE.value
            )
            audit_timeout.event_metadata = {
                "error": rzp_res.get("error"),
                "lifecycle_stage": "AUTHORIZED",
                "notes": order_notes,
                "resolution": "Transaction safely held in AUTHORIZED reserve for idempotent retry without duplicate charges."
            }
            db.add(audit_timeout)
            db.commit()
            return TransactionService.format_transaction_response(transaction, db, policy_result)

        if rzp_res.get("status") == "PAYMENT_SUCCESS":
            # Phase 2A (Success): Commit Reservation Permanently (CAPTURED)
            payment_service.commit_payment(
                payment_intent=payment_intent,
                provider_payment_id=rzp_res.get("provider_payment_id"),
                db=db
            )
            commit_budget = PolicyEngine.get_budget_summary(agent_id, db)

            audit_commit = AuditEvent(
                id=f"audit_{uuid.uuid4().hex[:12]}",
                transaction_id=tx_id,
                event_type="BUDGET_COMMITTED",
                actor_type=ActorType.PAYMENT_SERVICE.value
            )
            audit_commit.event_metadata = {
                "committed_amount": amount,
                "currency": currency,
                "provider_payment_id": payment_intent.provider_payment_id,
                "spent_today": commit_budget["spent_today"],
                "currently_reserved": commit_budget["currently_reserved"],
                "available_budget": commit_budget["available_budget"],
                "lifecycle_stage": "CAPTURED",
                "note": "Reserved funds permanently committed upon successful payment capture (PaymentIntent: CAPTURED)"
            }
            db.add(audit_commit)
            db.commit()

            TransactionStateMachine.transition(
                transaction=transaction,
                target_status=TransactionStatus.PAYMENT_SUCCESS.value,
                actor_type=ActorType.PAYMENT_SERVICE.value,
                event_type="PAYMENT_CAPTURED_SUCCESSFULLY",
                metadata={
                    "payment_intent_id": payment_intent.id,
                    "provider_payment_id": payment_intent.provider_payment_id,
                    "amount": payment_intent.amount,
                    "lifecycle_stage": "CAPTURED"
                },
                db=db
            )

            # Confirm Order with Merchant
            order_confirmation = MerchantService.confirm_order(product_id=product_id, quantity=1, db=db)
            TransactionStateMachine.transition(
                transaction=transaction,
                target_status=TransactionStatus.ORDER_CONFIRMED.value,
                actor_type=ActorType.MERCHANT_SERVICE.value,
                event_type="MERCHANT_ORDER_CONFIRMED",
                metadata=order_confirmation,
                db=db
            )

            # Generate Receipt
            receipt = ReceiptService.generate_receipt(transaction, db)
            TransactionStateMachine.transition(
                transaction=transaction,
                target_status=TransactionStatus.RECEIPT_GENERATED.value,
                actor_type=ActorType.SYSTEM.value,
                event_type="RECEIPT_ISSUED",
                metadata={"receipt_id": receipt.id, "receipt_number": receipt.receipt_number},
                db=db
            )
        else:
            # Phase 2B (Failure): Release Reservation & Restore Available Budget! (RELEASED)
            err_desc = rzp_res.get("error", {}).get("description", "Payment declined by issuing bank.")
            payment_service.release_payment(
                payment_intent=payment_intent,
                db=db,
                reason=err_desc
            )
            release_budget = PolicyEngine.get_budget_summary(agent_id, db)

            audit_release = AuditEvent(
                id=f"audit_{uuid.uuid4().hex[:12]}",
                transaction_id=tx_id,
                event_type="BUDGET_RELEASED",
                actor_type=ActorType.PAYMENT_SERVICE.value
            )
            audit_release.event_metadata = {
                "released_amount": amount,
                "currency": currency,
                "reason": err_desc,
                "spent_today": release_budget["spent_today"],
                "currently_reserved": release_budget["currently_reserved"],
                "available_budget": release_budget["available_budget"],
                "lifecycle_stage": "RELEASED",
                "note": "Reservation voided upon payment failure. Available budget immediately restored."
            }
            db.add(audit_release)
            db.commit()

            TransactionStateMachine.transition(
                transaction=transaction,
                target_status=TransactionStatus.PAYMENT_FAILED.value,
                actor_type=ActorType.PAYMENT_SERVICE.value,
                event_type="PAYMENT_AUTHORIZATION_FAILED",
                metadata={
                    "payment_intent_id": payment_intent.id,
                    "error": err_desc,
                    "reservation_released": True,
                    "released_amount": amount,
                    "restored_available_budget": release_budget["available_budget"],
                    "lifecycle_stage": "RELEASED"
                },
                db=db
            )

        return TransactionService.format_transaction_response(transaction, db, policy_result)

    @staticmethod
    def create_and_process_intent(
        agent_id: str,
        merchant_id: str,
        product_id: str,
        amount: float,
        currency: str = "INR",
        idempotency_key: Optional[str] = None,
        simulate_failure: bool = False,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Main two-phase reserve-then-commit orchestration pipeline:
        1. Phase 1 (Reserve): Locks funds against daily budget on approval (PaymentIntent: AUTHORIZED)
        2. Phase 2 (Commit or Release): Executes Razorpay rail. On success commits (CAPTURED),
           on decline/failure immediately voids and releases hold (RELEASED).
        """
        reserve_result = TransactionService.create_and_reserve_intent(
            agent_id=agent_id,
            merchant_id=merchant_id,
            product_id=product_id,
            amount=amount,
            currency=currency,
            idempotency_key=idempotency_key,
            db=db
        )

        policy_res = reserve_result.get("policy_result")
        if policy_res and not policy_res.approved:
            return reserve_result["formatted"]

        tx = reserve_result["transaction"]
        pi = reserve_result.get("payment_intent")
        if not pi or tx.status in (TransactionStatus.PAYMENT_SUCCESS.value, TransactionStatus.PAYMENT_FAILED.value, TransactionStatus.RECEIPT_GENERATED.value):
            return reserve_result["formatted"]

        return TransactionService.finalize_payment(
            transaction=tx,
            payment_intent=pi,
            db=db,
            simulate_failure=simulate_failure,
            idempotency_key=idempotency_key,
            policy_result=policy_res,
            pre_reserve_budget=reserve_result.get("pre_reserve_budget"),
            budget_reserve_snapshot=reserve_result.get("budget_reserve_snapshot")
        )

    @staticmethod
    def get_transaction(transaction_id: str, db: Session) -> Optional[Dict[str, Any]]:
        tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not tx:
            return None
        return TransactionService.format_transaction_response(tx, db)

    @staticmethod
    def list_transactions(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
        txs = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(limit).all()
        return [TransactionService.format_transaction_response(tx, db) for tx in txs]

    @staticmethod
    def format_transaction_response(
        tx: Transaction,
        db: Session,
        policy_result: Optional[Any] = None
    ) -> Dict[str, Any]:
        pi = tx.purchase_intent
        receipt = tx.receipt
        audit_events = db.query(AuditEvent).filter(AuditEvent.transaction_id == tx.id).order_by(AuditEvent.created_at.asc()).all()

        # Fetch payment intent if available
        pay_int = db.query(PaymentIntent).filter(PaymentIntent.purchase_intent_id == pi.id).first() if pi else None
        budget_summary = PolicyEngine.get_budget_summary(pi.agent_id, db) if pi else None

        # Build budget lifecycle breakdown from audit events
        lifecycle_events = []
        for ev in audit_events:
            if ev.event_type in ("BUDGET_RESERVED", "BUDGET_COMMITTED", "BUDGET_RELEASED"):
                lifecycle_events.append({
                    "event_type": ev.event_type,
                    "lifecycle_stage": ev.event_metadata.get("lifecycle_stage"),
                    "amount": ev.event_metadata.get("reserved_amount") or ev.event_metadata.get("committed_amount") or ev.event_metadata.get("released_amount"),
                    "available_budget": ev.event_metadata.get("available_budget"),
                    "currently_reserved": ev.event_metadata.get("currently_reserved"),
                    "spent_today": ev.event_metadata.get("spent_today"),
                    "note": ev.event_metadata.get("note"),
                    "created_at": ev.created_at.isoformat() if ev.created_at else None
                })

        reserve_ev = next((e for e in lifecycle_events if e["event_type"] == "BUDGET_RESERVED"), None)
        release_ev = next((e for e in lifecycle_events if e["event_type"] == "BUDGET_RELEASED"), None)
        commit_ev = next((e for e in lifecycle_events if e["event_type"] == "BUDGET_COMMITTED"), None)

        pre_reserve = (reserve_ev["available_budget"] + pi.amount) if (reserve_ev and pi and "available_budget" in reserve_ev and reserve_ev["available_budget"] is not None) else (budget_summary["available_budget"] if budget_summary else 20000.0)
        post_reserve = reserve_ev["available_budget"] if reserve_ev else None

        budget_lifecycle = {
            "has_reservation": reserve_ev is not None,
            "lifecycle_stage": pay_int.status if pay_int else ("DENIED" if tx.status == "DENIED" else tx.status),
            "reserved_amount": pi.amount if (pi and reserve_ev) else 0.0,
            "pre_reserve_available": pre_reserve,
            "post_reserve_available": post_reserve,
            "final_available": budget_summary["available_budget"] if budget_summary else 20000.0,
            "currently_reserved": budget_summary["currently_reserved"] if budget_summary else 0.0,
            "net_debited": pi.amount if commit_ev else 0.0,
            "is_committed": commit_ev is not None,
            "is_released": release_ev is not None,
            "events": lifecycle_events
        }

        return {
            "id": tx.id,
            "status": tx.status,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
            "updated_at": tx.updated_at.isoformat() if tx.updated_at else None,
            "purchase_intent": {
                "id": pi.id if pi else None,
                "agent_id": pi.agent_id if pi else None,
                "merchant_id": pi.merchant_id if pi else None,
                "product_id": pi.product_id if pi else None,
                "amount": pi.amount if pi else None,
                "currency": pi.currency if pi else "INR",
                "status": pi.status if pi else None
            } if pi else None,
            "payment_intent_id": tx.payment_intent_id,
            "payment_intent": {
                "id": pay_int.id if pay_int else None,
                "status": pay_int.status if pay_int else None,
                "provider": pay_int.provider if pay_int else "RAZORPAY",
                "provider_payment_id": pay_int.provider_payment_id if pay_int else None,
                "amount": pay_int.amount if pay_int else None,
                "currency": pay_int.currency if pay_int else "INR",
                "reserved_at": pay_int.reserved_at.isoformat() if (pay_int and pay_int.reserved_at) else None,
                "committed_at": pay_int.committed_at.isoformat() if (pay_int and pay_int.committed_at) else None,
                "released_at": pay_int.released_at.isoformat() if (pay_int and pay_int.released_at) else None
            } if pay_int else None,
            "budget_summary": budget_summary,
            "budget_lifecycle": budget_lifecycle,
            "policy_result": policy_result.to_dict() if policy_result else None,
            "receipt": {
                "id": receipt.id,
                "receipt_number": receipt.receipt_number,
                "amount": receipt.amount,
                "currency": receipt.currency,
                "details": receipt.details
            } if receipt else None,
            "audit_events": [
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "actor_type": event.actor_type,
                    "metadata": event.event_metadata,
                    "created_at": event.created_at.isoformat() if event.created_at else None
                }
                for event in audit_events
            ]
        }
