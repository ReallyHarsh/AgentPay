"""
Official AgentPay Model Context Protocol (MCP) Server.
Standardized tool exposure conforming to the Model Context Protocol specification.
Allows AI Buyer Agents (Claude, GPT, etc.) to securely interact with merchant catalogs,
quote pricing, and formulate purchase intents under strict policy rail supervision.
"""
import json
import logging
from typing import Optional, List, Dict, Any
from mcp.server.mcpserver import MCPServer
from agentpay.database.models import SessionLocal, Product
from agentpay.merchants.service import MerchantService
from agentpay.transactions.service import TransactionService
from agentpay.receipts.service import ReceiptService
from agentpay.agents.intent import IntentAgent

logger = logging.getLogger("agentpay.mcp")

# Forbidden tools security invariant: financial rails cannot be exposed over MCP
FORBIDDEN_TOOLS = {
    "charge_card",
    "transfer_money",
    "modify_policy",
    "modify_limits",
    "access_payment_credentials",
    "direct_debit",
    "authorize_payment"
}


def create_mcp_server(agent_id: str = "agent_001") -> MCPServer:
    """
    Constructs and registers the AgentPay Model Context Protocol Server.
    Exposes safe commerce discovery, quote evaluation, and intent creation tools.
    """
    server = MCPServer("AgentPay-MCP-Server")

    @server.tool(
        name="search_products",
        description="Deep multi-attribute semantic search across federated merchant inventory using dense vector embeddings (all-MiniLM-L6-v2). Enforces price ceilings and category matching."
    )
    def search_products(
        query: str,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        brand: Optional[str] = None,
        feature_keywords: Optional[List[str]] = None
    ) -> str:
        """Search products in catalog using semantic embeddings."""
        db = SessionLocal()
        try:
            results = MerchantService.search_products(
                query=query,
                category=category,
                max_price=max_price,
                min_price=min_price,
                brand=brand,
                feature_keywords=feature_keywords,
                db=db
            )
            return json.dumps({
                "products_found": len(results),
                "products": results[:10]
            })
        finally:
            db.close()

    @server.tool(
        name="get_quote",
        description="Fetch verified real-time pricing, stock availability, and technical specs for a specific product ID across merchant nodes (Croma, Reliance, Amazon)."
    )
    def get_quote(product_id: str) -> str:
        """Fetch real-time merchant quote and inventory status."""
        db = SessionLocal()
        try:
            quote = MerchantService.get_quote(product_id=product_id, db=db)
            if not quote:
                return json.dumps({"error": "PRODUCT_NOT_FOUND", "message": f"Product '{product_id}' not found."})
            return json.dumps({"quote": quote})
        finally:
            db.close()

    @server.tool(
        name="create_purchase_intent",
        description="Formulates and submits an official purchase intent to the AgentPay Gateway. Triggers automated policy evaluation and Phase 1 atomic budget reservation (AUTHORIZED)."
    )
    def create_purchase_intent(
        product_id: str,
        amount: float,
        merchant_id: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> str:
        """Submit purchase intent to AgentPay Gateway for policy validation & reservation."""
        db = SessionLocal()
        try:
            resolved_merchant_id = merchant_id
            if not resolved_merchant_id:
                product = db.query(Product).filter(Product.id == product_id).first()
                resolved_merchant_id = product.merchant_id if product else "merchant_001"

            # Enforce atomic reserve-then-commit lifecycle
            result = TransactionService.create_and_reserve_intent(
                agent_id=agent_id,
                merchant_id=resolved_merchant_id,
                product_id=product_id,
                amount=amount,
                idempotency_key=idempotency_key,
                db=db
            )
            # result["formatted"] is the clean JSON-serializable representation
            return json.dumps(result.get("formatted", {
                "transaction_id": result.get("transaction", {}).id if hasattr(result.get("transaction"), "id") else None,
                "status": "AUTHORIZED"
            }))
        finally:
            db.close()

    @server.tool(
        name="get_transaction_status",
        description="Inspect real-time state machine status, two-phase budget reservation lifecycle, and cryptographic audit log for a transaction ID."
    )
    def get_transaction_status(transaction_id: str) -> str:
        """Inspect transaction state machine and budget lifecycle."""
        db = SessionLocal()
        try:
            tx = TransactionService.get_transaction(transaction_id=transaction_id, db=db)
            if not tx:
                return json.dumps({"error": "TRANSACTION_NOT_FOUND", "message": f"Transaction '{transaction_id}' not found."})
            return json.dumps({"transaction": tx})
        finally:
            db.close()

    @server.tool(
        name="get_receipt",
        description="Retrieve official cryptographically verifiable tax receipt for a successfully committed (CAPTURED) transaction."
    )
    def get_receipt(receipt_id: str) -> str:
        """Fetch verified tax receipt."""
        db = SessionLocal()
        try:
            receipt = ReceiptService.get_receipt(receipt_id=receipt_id, db=db)
            if not receipt:
                return json.dumps({"error": "RECEIPT_NOT_FOUND", "message": f"Receipt '{receipt_id}' not found."})
            return json.dumps({"receipt": receipt})
        finally:
            db.close()

    @server.tool(
        name="request_clarification",
        description="Requests interactive human-in-the-loop clarification when a user query is broad or underspecified."
    )
    def request_clarification(raw_message: str, category: Optional[str] = None) -> str:
        """Disambiguate broad queries with interactive options."""
        intent_data = IntentAgent.parse_intent(raw_message)
        return json.dumps({
            "clarification_required": True,
            "question": intent_data.get("clarifying_question"),
            "options": intent_data.get("clarification_options", [])
        })

    return server


# Global singleton instance
_GLOBAL_MCP_SERVER: Optional[MCPServer] = None


def get_mcp_server(agent_id: str = "agent_001") -> MCPServer:
    """Returns the singleton AgentPay MCPServer instance."""
    global _GLOBAL_MCP_SERVER
    if _GLOBAL_MCP_SERVER is None:
        _GLOBAL_MCP_SERVER = create_mcp_server(agent_id=agent_id)
    return _GLOBAL_MCP_SERVER


async def get_mcp_tools_list(agent_id: str = "agent_001") -> List[Dict[str, Any]]:
    """
    Returns the standardized list of MCP tools serialized to JSON-compatible dictionaries,
    including their JSON schema and descriptions.
    """
    server = get_mcp_server(agent_id=agent_id)
    tools = await server.list_tools()
    return [t.model_dump(by_alias=True) for t in tools]
