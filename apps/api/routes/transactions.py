from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from agentpay.database.models import get_db, Transaction
from agentpay.transactions.service import TransactionService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


class FinalizeTransactionRequest(BaseModel):
    simulate_failure: bool = Field(False, json_schema_extra={"example": False})


@router.get("")
def list_transactions(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List all transactions with audit logs and current state.
    """
    return TransactionService.list_transactions(db=db, limit=limit)


@router.get("/{transaction_id}")
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed transaction state, status, and immutable audit trail.
    Used for timeline polling and verification.
    """
    tx = TransactionService.get_transaction(transaction_id=transaction_id, db=db)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.post("/{transaction_id}/finalize")
def finalize_transaction(
    transaction_id: str,
    payload: FinalizeTransactionRequest = FinalizeTransactionRequest(),
    db: Session = Depends(get_db)
):
    """
    Phase 2 (Commit or Release): Executes the payment call on the Razorpay rail.
    If payment succeeds: commits PaymentIntent (CAPTURED) and generates receipt.
    If payment fails: releases PaymentIntent (RELEASED) and voids reservation.
    """
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if not tx.purchase_intent or not tx.purchase_intent.payment_intent:
        raise HTTPException(status_code=400, detail="Transaction does not have an active payment reservation")

    result = TransactionService.finalize_payment(
        transaction=tx,
        payment_intent=tx.purchase_intent.payment_intent,
        db=db,
        simulate_failure=payload.simulate_failure
    )
    return result
