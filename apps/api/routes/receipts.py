from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from agentpay.database.models import get_db
from agentpay.receipts.service import ReceiptService

router = APIRouter(prefix="/receipts", tags=["Receipts"])


@router.get("/{receipt_id}")
def get_receipt(
    receipt_id: str,
    db: Session = Depends(get_db)
):
    """
    Get official transaction receipt by Receipt ID or Receipt Number.
    """
    rcpt = ReceiptService.get_receipt(receipt_id=receipt_id, db=db)
    if not rcpt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return {
        "id": rcpt.id,
        "transaction_id": rcpt.transaction_id,
        "receipt_number": rcpt.receipt_number,
        "amount": rcpt.amount,
        "currency": rcpt.currency,
        "status": rcpt.status,
        "details": rcpt.details,
        "created_at": rcpt.created_at.isoformat() if rcpt.created_at else None
    }
