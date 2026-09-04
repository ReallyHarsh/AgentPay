import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from agentpay.database.models import Receipt, Transaction, Product


class ReceiptService:
    @staticmethod
    def generate_receipt(transaction: Transaction, db: Session) -> Receipt:
        """
        Generates and persists an official AgentPay audit receipt for a completed transaction.
        """
        # Check if receipt already exists
        existing = db.query(Receipt).filter(Receipt.transaction_id == transaction.id).first()
        if existing:
            return existing

        purchase_intent = transaction.purchase_intent
        product = db.query(Product).filter(Product.id == purchase_intent.product_id).first() if purchase_intent else None

        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        rand_suffix = uuid.uuid4().hex[:6].upper()
        receipt_number = f"RCPT-{date_str}-{rand_suffix}"

        details = {
            "transaction_id": transaction.id,
            "purchase_intent_id": purchase_intent.id if purchase_intent else None,
            "payment_intent_id": transaction.payment_intent_id,
            "agent_id": purchase_intent.agent_id if purchase_intent else "agent_001",
            "merchant_id": purchase_intent.merchant_id if purchase_intent else "merchant_001",
            "product_id": purchase_intent.product_id if purchase_intent else None,
            "product_name": product.name if product else "Purchased Item",
            "category": product.category if product else "General",
            "amount": purchase_intent.amount if purchase_intent else 0.0,
            "currency": purchase_intent.currency if purchase_intent else "INR",
            "payment_provider": "RAZORPAY",
            "issued_at": datetime.now(timezone.utc).isoformat()
        }

        receipt = Receipt(
            id=f"rcpt_{uuid.uuid4().hex[:12]}",
            transaction_id=transaction.id,
            receipt_number=receipt_number,
            amount=purchase_intent.amount if purchase_intent else 0.0,
            currency=purchase_intent.currency if purchase_intent else "INR",
            status="ISSUED"
        )
        receipt.details = details

        db.add(receipt)
        db.commit()
        db.refresh(receipt)
        return receipt

    @staticmethod
    def get_receipt(receipt_id: str, db: Session) -> Optional[Receipt]:
        return db.query(Receipt).filter(
            (Receipt.id == receipt_id) | (Receipt.receipt_number == receipt_id)
        ).first()
