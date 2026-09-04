from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from agentpay.database.models import get_db
from agentpay.transactions.service import TransactionService

router = APIRouter(prefix="/purchase-intents", tags=["Purchase Intents"])


class PurchaseIntentRequest(BaseModel):
    agent_id: str = Field("agent_001", json_schema_extra={"example": "agent_001"})
    merchant_id: str = Field("merchant_001", json_schema_extra={"example": "merchant_001"})
    product_id: str = Field(..., json_schema_extra={"example": "prod_jbl_770nc"})
    amount: float = Field(..., json_schema_extra={"example": 4499.0})
    currency: str = Field("INR", json_schema_extra={"example": "INR"})
    idempotency_key: Optional[str] = Field(None, json_schema_extra={"example": "idem_12345678"})


@router.post("")
def create_purchase_intent(
    payload: PurchaseIntentRequest,
    x_idempotency_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Called by AI Buyer to initiate purchase.
    Enforces deterministic state progression:
    CREATED -> POLICY_CHECKED -> APPROVED/DENIED -> PAYMENT -> RECEIPT
    """
    idempotency_key = payload.idempotency_key or x_idempotency_key
    try:
        result = TransactionService.create_and_process_intent(
            agent_id=payload.agent_id,
            merchant_id=payload.merchant_id,
            product_id=payload.product_id,
            amount=payload.amount,
            currency=payload.currency,
            idempotency_key=idempotency_key,
            db=db
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transaction processing error: {str(e)}")


@router.post("/reserve")
def reserve_purchase_intent(
    payload: PurchaseIntentRequest,
    x_idempotency_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Phase 1 (Reserve): Evaluates policy. If approved, immediately reserves funds
    against daily spending limit and creates PaymentIntent in AUTHORIZED status.
    If denied, terminates immediately with zero funds reserved.
    """
    idempotency_key = payload.idempotency_key or x_idempotency_key
    try:
        result = TransactionService.create_and_reserve_intent(
            agent_id=payload.agent_id,
            merchant_id=payload.merchant_id,
            product_id=payload.product_id,
            amount=payload.amount,
            currency=payload.currency,
            idempotency_key=idempotency_key,
            db=db
        )
        return result["formatted"]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transaction reservation error: {str(e)}")
