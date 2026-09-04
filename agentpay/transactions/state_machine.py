import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from agentpay.database.models import (
    Transaction,
    AuditEvent,
    TransactionStatus,
    ActorType
)


class InvalidStateTransitionError(Exception):
    pass


class TransactionStateMachine:
    """
    Guarantees deterministic state transitions for AgentPay transactions.
    Enforces that:
    1. Only approved purchase intents can proceed to payment.
    2. Denied purchase intents are terminal (no payment ever created or attempted).
    3. Every transition appends an immutable AuditEvent.
    """

    ALLOWED_TRANSITIONS = {
        TransactionStatus.CREATED.value: [TransactionStatus.POLICY_CHECKED.value],
        TransactionStatus.POLICY_CHECKED.value: [
            TransactionStatus.APPROVED.value,
            TransactionStatus.DENIED.value
        ],
        TransactionStatus.APPROVED.value: [
            TransactionStatus.PAYMENT_CREATED.value
        ],
        TransactionStatus.DENIED.value: [],  # Terminal state
        TransactionStatus.PAYMENT_CREATED.value: [
            TransactionStatus.PAYMENT_SUCCESS.value,
            TransactionStatus.PAYMENT_FAILED.value
        ],
        TransactionStatus.PAYMENT_SUCCESS.value: [
            TransactionStatus.ORDER_CONFIRMED.value
        ],
        TransactionStatus.PAYMENT_FAILED.value: [],  # Terminal state
        TransactionStatus.ORDER_CONFIRMED.value: [
            TransactionStatus.RECEIPT_GENERATED.value
        ],
        TransactionStatus.RECEIPT_GENERATED.value: []  # Final completed state
    }

    @classmethod
    def transition(
        cls,
        transaction: Transaction,
        target_status: str,
        actor_type: str,
        event_type: str,
        metadata: Dict[str, Any],
        db: Session
    ) -> Transaction:
        current_status = transaction.status

        # If already in target status, return idempotently
        if current_status == target_status:
            return transaction

        valid_targets = cls.ALLOWED_TRANSITIONS.get(current_status, [])
        if target_status not in valid_targets:
            raise InvalidStateTransitionError(
                f"Cannot transition transaction {transaction.id} from {current_status} to {target_status}. Allowed next states: {valid_targets}"
            )

        # Update status
        transaction.status = target_status
        transaction.updated_at = datetime.now(timezone.utc)
        db.add(transaction)

        # Append immutable audit event
        audit_event = AuditEvent(
            id=f"audit_{uuid.uuid4().hex[:12]}",
            transaction_id=transaction.id,
            event_type=event_type,
            actor_type=actor_type,
            created_at=datetime.now(timezone.utc)
        )
        audit_event.event_metadata = metadata
        db.add(audit_event)

        db.commit()
        db.refresh(transaction)
        return transaction
