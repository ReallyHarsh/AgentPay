from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from agentpay.database.models import get_db, PurchaseIntent
from agentpay.payments.service import PaymentService

router = APIRouter(prefix="/payment-intents", tags=["Payments"])


class PaymentIntentRequest(BaseModel):
    purchase_intent_id: str = Field(..., json_schema_extra={"example": "pi_123456"})


@router.post("")
def create_payment_intent(
    payload: PaymentIntentRequest,
    db: Session = Depends(get_db)
):
    """
    Direct payment intent trigger (internally called after policy approval).
    """
    purchase_intent = db.query(PurchaseIntent).filter(PurchaseIntent.id == payload.purchase_intent_id).first()
    if not purchase_intent:
        raise HTTPException(status_code=404, detail="Purchase intent not found")

    if purchase_intent.status != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot initiate payment for purchase intent with status '{purchase_intent.status}'. Must be APPROVED by Policy Engine."
        )

    payment_service = PaymentService()
    payment_intent = payment_service.process_payment_for_intent(purchase_intent, db)
    return {
        "id": payment_intent.id,
        "purchase_intent_id": payment_intent.purchase_intent_id,
        "provider": payment_intent.provider,
        "provider_payment_id": payment_intent.provider_payment_id,
        "amount": payment_intent.amount,
        "currency": payment_intent.currency,
        "status": payment_intent.status
    }
