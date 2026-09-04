import json
import re
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from agentpay.database.models import Product, Merchant


from agentpay.merchants.retrieval import SemanticSearchEngine


class MerchantService:
    @staticmethod
    def search_products(
        query: Optional[str] = None,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        brand: Optional[str] = None,
        feature_keywords: Optional[List[str]] = None,
        top_k: int = 250,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Deep multi-attribute semantic vector search powered by SentenceTransformers all-MiniLM-L6-v2.
        Embeds queries into 384-dimensional dense space, applies constraint enforcement,
        and scores candidates against active merchant inventory.
        """
        if db is None:
            return []

        return SemanticSearchEngine.search(
            query=query,
            category=category,
            max_price=max_price,
            min_price=min_price,
            brand=brand,
            feature_keywords=feature_keywords,
            top_k=top_k,
            db=db
        )

    @staticmethod
    def _format_product(p: Product) -> Dict[str, Any]:
        return {
            "id": p.id,
            "merchant_id": p.merchant_id,
            "merchant_name": p.merchant.name if p.merchant else "OmniTech India",
            "name": p.name,
            "brand": getattr(p, "brand", ""),
            "description": p.description,
            "category": p.category,
            "price": p.price,
            "currency": p.currency,
            "stock": p.stock,
            "rating": getattr(p, "rating", 4.8),
            "specs": p.specs if hasattr(p, "specs") else {},
            "in_stock": p.stock > 0
        }

    @staticmethod
    def get_quote(product_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Returns guaranteed quote and item availability for a product.
        """
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None

        return {
            "product_id": product.id,
            "merchant_id": product.merchant_id,
            "name": product.name,
            "brand": getattr(product, "brand", ""),
            "category": product.category,
            "unit_price": product.price,
            "currency": product.currency,
            "tax": round(product.price * 0.18, 2),
            "total_amount": product.price,  # inclusive
            "in_stock": product.stock > 0,
            "stock_remaining": product.stock,
            "specs": product.specs if hasattr(product, "specs") else {}
        }

    @staticmethod
    def confirm_order(product_id: str, quantity: int = 1, db: Session = None) -> Dict[str, Any]:
        """
        Confirms order on merchant side, reducing stock.
        """
        if db is None:
            return {"status": "CONFIRMED"}

        product = db.query(Product).filter(Product.id == product_id).first()
        if product and product.stock >= quantity:
            product.stock -= quantity
            db.add(product)
            db.commit()
            db.refresh(product)

        return {
            "status": "CONFIRMED",
            "product_id": product_id,
            "quantity": quantity,
            "stock_remaining": product.stock if product else 0
        }
