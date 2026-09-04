from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from agentpay.database.models import get_db
from agentpay.merchants.service import MerchantService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("")
def list_products(
    query: Optional[str] = Query(None, description="Search query for product title or category"),
    category: Optional[str] = Query(None, description="Filter by category"),
    max_price: Optional[float] = Query(None, description="Max price filter"),
    limit: Optional[int] = Query(250, description="Max products to return"),
    db: Session = Depends(get_db)
):
    """
    Search available products from merchant catalog.
    Used by AI Buyer's `search_products` tool.
    """
    return MerchantService.search_products(
        query=query,
        category=category,
        max_price=max_price,
        top_k=limit or 250,
        db=db
    )


@router.get("/{product_id}/quote")
def get_product_quote(
    product_id: str,
    db: Session = Depends(get_db)
):
    """
    Get guaranteed price and availability quote.
    """
    quote = MerchantService.get_quote(product_id=product_id, db=db)
    if not quote:
        return {"error": "Product not found"}
    return quote
