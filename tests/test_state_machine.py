import pytest
from agentpay.database.models import Transaction, AuditEvent, TransactionStatus, ActorType
from agentpay.transactions.state_machine import TransactionStateMachine, InvalidStateTransitionError


def test_valid_state_machine_flow(db_session):
    tx = Transaction(id="tx_test_01", purchase_intent_id="pi_01", status=TransactionStatus.CREATED.value)
    db_session.add(tx)
    db_session.commit()

    # CREATED -> POLICY_CHECKED
    tx = TransactionStateMachine.transition(
        transaction=tx,
        target_status=TransactionStatus.POLICY_CHECKED.value,
        actor_type=ActorType.POLICY_ENGINE.value,
        event_type="POLICY_CHECK_STARTED",
        metadata={},
        db=db_session
    )
    assert tx.status == TransactionStatus.POLICY_CHECKED.value

    # POLICY_CHECKED -> APPROVED
    tx = TransactionStateMachine.transition(
        transaction=tx,
        target_status=TransactionStatus.APPROVED.value,
        actor_type=ActorType.POLICY_ENGINE.value,
        event_type="POLICY_APPROVED",
        metadata={},
        db=db_session
    )
    assert tx.status == TransactionStatus.APPROVED.value

    # Verify audit events were written
    events = db_session.query(AuditEvent).filter(AuditEvent.transaction_id == "tx_test_01").all()
    assert len(events) == 2


def test_invalid_state_transition_raises_error(db_session):
    tx = Transaction(id="tx_test_02", purchase_intent_id="pi_02", status=TransactionStatus.CREATED.value)
    db_session.add(tx)
    db_session.commit()

    # Attempting to jump directly from CREATED to PAYMENT_SUCCESS should fail
    with pytest.raises(InvalidStateTransitionError):
        TransactionStateMachine.transition(
            transaction=tx,
            target_status=TransactionStatus.PAYMENT_SUCCESS.value,
            actor_type=ActorType.PAYMENT_SERVICE.value,
            event_type="INVALID_JUMP",
            metadata={},
            db=db_session
        )


def test_denied_state_is_terminal(db_session):
    tx = Transaction(id="tx_test_03", purchase_intent_id="pi_03", status=TransactionStatus.POLICY_CHECKED.value)
    db_session.add(tx)
    db_session.commit()

    # POLICY_CHECKED -> DENIED
    tx = TransactionStateMachine.transition(
        transaction=tx,
        target_status=TransactionStatus.DENIED.value,
        actor_type=ActorType.POLICY_ENGINE.value,
        event_type="POLICY_DENIED",
        metadata={},
        db=db_session
    )
    assert tx.status == TransactionStatus.DENIED.value

    # Any subsequent transition from DENIED must fail
    with pytest.raises(InvalidStateTransitionError):
        TransactionStateMachine.transition(
            transaction=tx,
            target_status=TransactionStatus.PAYMENT_CREATED.value,
            actor_type=ActorType.PAYMENT_SERVICE.value,
            event_type="TRYING_TO_PAY_DENIED",
            metadata={},
            db=db_session
        )
