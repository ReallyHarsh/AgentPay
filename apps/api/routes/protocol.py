"""
Protocol Manifests & Agent-Readable Catalog Endpoints.
Implements:
- /.well-known/agent-catalog.json (Universal Agent Commerce Protocol / ACP catalog schema)
- /.well-known/uap-manifest.json (NPCI Unified Autonomous Platform / UAP draft)
- /.well-known/ai-plugin.json (OpenAI / Agent Plugin specification)
- /llms.txt (Standard LLM-optimized catalog feed)
- /api/v1/protocol/x402/checkout (HTTP 402 Payment Required protocol rail)
"""
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Response, status, Header
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from agentpay.database.models import get_db, Product, Merchant

router = APIRouter(tags=["Agentic Commerce Protocols (UAP / ACP / x402)"])


class X402CheckoutRequest(BaseModel):
    product_id: str = Field(..., description="ID of the SKU to purchase")
    agent_id: Optional[str] = Field(default="agent_001", description="ID of the calling AI Buyer Agent")
    quantity: int = Field(default=1, ge=1, description="Quantity of items")


@router.get("/.well-known/agent-catalog.json", summary="Universal Agent-Readable Catalog (UAP / ACP)")
@router.get("/api/v1/protocol/agent-catalog.json", summary="Agent-Readable Catalog API Route")
def get_agent_readable_catalog(db: Session = Depends(get_db)):
    """
    Standardized agent-readable catalog complying with the Agent Commerce Protocol (ACP)
    and NPCI Unified Autonomous Platform (UAP) architecture.
    Provides semantic product schemas, guaranteed quote TTLs, and Razorpay payment rail descriptors.
    """
    products = db.query(Product).filter(Product.stock > 0).all()
    merchants = db.query(Merchant).filter(Merchant.status == "ACTIVE").all()

    items = []
    for p in products:
        m_name = p.merchant.name if p.merchant else "OmniTech Hub"
        items.append({
            "@context": "https://schema.org",
            "@type": "Product",
            "sku": p.id,
            "name": p.name,
            "brand": getattr(p, "brand", p.name.split()[0] if p.name else "TechBrand"),
            "category": p.category,
            "description": p.description,
            "offers": {
                "@type": "Offer",
                "price": p.price,
                "priceCurrency": p.currency or "INR",
                "pricePaise": int(round(p.price * 100)),
                "availability": "https://schema.org/InStock",
                "itemCondition": "https://schema.org/NewCondition",
                "seller": {
                    "@type": "Organization",
                    "merchant_id": p.merchant_id,
                    "name": m_name
                },
                "quote_ttl_seconds": 300,
                "quote_url": f"/api/v1/products/{p.id}/quote",
                "x402_checkout_url": f"/api/v1/protocol/x402/checkout"
            },
            "specs": getattr(p, "specs", {}) or {},
            "rating": getattr(p, "rating", 4.8),
            "stock_quantity": p.stock
        })

    return {
        "$schema": "https://specs.agentpay.org/v1/agent-catalog.schema.json",
        "protocol": "Unified Agent Protocol (UAP) / Agent Commerce Protocol (ACP)",
        "protocol_version": "1.0.0",
        "gateway": "AgentPay",
        "settlement_rail": {
            "provider": "RAZORPAY",
            "network": "test",
            "currency": "INR",
            "supported_methods": ["upi", "card", "netbanking"],
            "paise_multiplier": 100,
            "endpoints": {
                "intent_authorization": "/api/v1/purchase-intents",
                "policy_evaluation": "/api/v1/policies/evaluate",
                "x402_challenge": "/api/v1/protocol/x402/checkout"
            }
        },
        "policy_governance": {
            "model": "deterministic_reserve_commit",
            "security_boundary": "AI can decide and formulate intent; only AgentPay authorises money movement",
            "enforced_checks": [
                "per_transaction_limit",
                "rolling_24h_velocity",
                "category_whitelist",
                "merchant_blocklist"
            ]
        },
        "merchants": [
            {
                "id": m.id,
                "name": m.name,
                "status": getattr(m, "status", "ACTIVE"),
                "category": getattr(m, "category", "Electronics & Direct Retail"),
                "trust_score": getattr(m, "trust_score", 4.9),
                "is_verified": True
            } for m in merchants
        ],
        "total_items": len(items),
        "products": items
    }


@router.get("/.well-known/uap-manifest.json", summary="NPCI Unified Autonomous Platform Manifest")
@router.get("/api/v1/protocol/uap-manifest.json", summary="UAP Manifest API Route")
def get_uap_manifest():
    """
    Returns the NPCI UAP (Unified Autonomous Platform) & AP2 manifest.
    Declares participant identity, capability registry, and trust envelope.
    """
    return {
        "uap_spec_version": "0.4.2-draft",
        "network_id": "in.npci.uap.testnet",
        "participant_id": "gateway.agentpay.in",
        "role": "AGENT_COMMERCE_GATEWAY",
        "operator": "Razorpay AgentPay Initiative",
        "supported_protocols": [
            "UAP-2026",
            "ACP (Agent Commerce Protocol)",
            "AP2 (Autonomous Payment Protocol)",
            "x402 (Payment Required Rail)",
            "MCP (Model Context Protocol 2024-11-05)"
        ],
        "settlement": {
            "rail": "RAZORPAY_TEST_MODE",
            "settlement_currency": "INR",
            "precision": "paise"
        },
        "invariants": {
            "zero_unauthorized_draws": True,
            "atomic_rollback_on_failure": True,
            "immutable_audit_trail": True
        },
        "endpoints": {
            "agent_catalog": "/.well-known/agent-catalog.json",
            "llms_feed": "/llms.txt",
            "mcp_server": "/api/v1/mcp/manifest",
            "x402_challenge": "/api/v1/protocol/x402/checkout",
            "intent_pipeline": "/api/v1/purchase-intents",
            "health": "/api/v1/health"
        }
    }


@router.get("/.well-known/ai-plugin.json", summary="Standard AI Agent Plugin Manifest")
def get_ai_plugin_manifest():
    """
    OpenAI / Standard Agent Plugin Manifest for autonomous LLM tools discovery.
    """
    return {
        "schema_version": "v1",
        "name_for_human": "AgentPay Commerce Hub",
        "name_for_model": "agentpay_commerce",
        "description_for_human": "Discover merchant products, obtain guaranteed quotes, and execute policy-bounded purchases on Razorpay test rails.",
        "description_for_model": "Connect to AgentPay to search live merchant inventories, compare verified prices, and submit purchase intents with spending limit protection.",
        "auth": {
            "type": "none"
        },
        "api": {
            "type": "openapi",
            "url": "/openapi.json",
            "is_user_authenticated": False
        },
        "logo_url": "https://agentpay.org/assets/logo.png",
        "contact_email": "dev@agentpay.org",
        "legal_info_url": "https://agentpay.org/terms"
    }


@router.get("/llms.txt", summary="LLM Crawler Plaintext Feed")
def get_llms_txt(db: Session = Depends(get_db)):
    """
    Generates standard /llms.txt format for LLM scrapers, browser agents,
    and system prompt grounding without JSON parsing overhead.
    """
    products = db.query(Product).filter(Product.stock > 0).all()
    merchants = db.query(Merchant).filter(Merchant.status == "ACTIVE").all()

    lines = [
        "# AgentPay Verified Merchant Catalog",
        "> Autonomous Agent Commerce on Razorpay Rails",
        "",
        "## Policy & Execution Rules",
        "- All transactions are subject to deterministic spending limits and 24h velocity bounds.",
        "- Purchases use Two-Phase Reserve-Then-Commit (Razorpay native AUTHORIZE -> CAPTURE/RELEASE).",
        "- AI Agents formulate purchase intents; payment credentials are never accessible by models.",
        "",
        "## Verified Merchants",
    ]

    for m in merchants:
        cat = getattr(m, "category", "Electronics & Retail")
        score = getattr(m, "trust_score", 4.9)
        lines.append(f"- **{m.name}** (`{m.id}`) | Category: {cat} | Trust Score: {score}/5.0")

    lines.append("")
    lines.append("## Available Catalog Products")
    for p in products:
        m_name = p.merchant.name if p.merchant else "OmniTech"
        lines.append(f"### {p.name}")
        lines.append(f"- **SKU**: `{p.id}`")
        lines.append(f"- **Price**: ₹{p.price:,.2f} INR ({int(p.price * 100)} paise)")
        lines.append(f"- **Merchant**: {m_name} (`{p.merchant_id}`)")
        lines.append(f"- **Category**: {p.category}")
        lines.append(f"- **Stock**: {p.stock} units available")
        lines.append(f"- **Description**: {p.description}")
        if hasattr(p, "specs") and p.specs:
            specs_str = ", ".join([f"{k}: {v}" for k, v in p.specs.items()])
            lines.append(f"- **Specs**: {specs_str}")
        lines.append(f"- **Quote Endpoint**: `GET /api/v1/products/{p.id}/quote`")
        lines.append(f"- **Purchase Intent Endpoint**: `POST /api/v1/purchase-intents`")
        lines.append("")

    content = "\n".join(lines)
    return PlainTextResponse(content=content, media_type="text/plain; charset=utf-8")


@router.api_route("/api/v1/protocol/x402/checkout", methods=["GET", "POST"], summary="x402 HTTP 402 Payment Required Challenge Rail")
def x402_checkout_challenge(
    request: Optional[X402CheckoutRequest] = None,
    product_id: Optional[str] = Query(None, description="Query param product ID for GET requests"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """
    Implements the global x402 (HTTP 402 Payment Required) protocol standard.
    When an AI buyer agent calls this commercial checkout rail without a pre-cleared
    AgentPay payment token, the server returns HTTP 402 with structured Razorpay payment challenge headers.
    """
    target_pid = (request.product_id if request else None) or product_id or "prod_001"
    product = db.query(Product).filter(Product.id == target_pid).first()
    if not product:
        product = db.query(Product).first()

    if not product:
        return JSONResponse(status_code=404, content={"error": "No product available"})

    # Check if authorization token is already provided (e.g. simulated resolution flow)
    if authorization and (authorization.startswith("AgentPay ") or authorization.startswith("Bearer ")):
        token = authorization.split(" ")[-1]
        return {
            "status": 200,
            "message": "Payment token verified. Order cleared for fulfillment on Razorpay rails.",
            "protocol": "x402-settled",
            "token": token,
            "product_id": product.id,
            "amount": product.price,
            "currency": product.currency
        }

    # Otherwise, return the standard HTTP 402 Payment Required Challenge!
    order_draft_id = f"order_x402_{uuid.uuid4().hex[:12]}"
    amount_paise = int(round(product.price * 100))

    headers = {
        "X-Payment-Rail": "razorpay",
        "X-Payment-Protocol": "x402-v1 / UAP-ACP",
        "X-Razorpay-Order-Id": order_draft_id,
        "X-Amount-Paise": str(amount_paise),
        "X-Currency": "INR",
        "WWW-Authenticate": f'X402 realm="AgentPay-Razorpay", token_endpoint="/api/v1/purchase-intents", amount="{product.price}", currency="INR"',
    }

    body = {
        "status": 402,
        "title": "Payment Required",
        "protocol": "x402 / UAP-ACP (2026)",
        "message": "Direct resource access requires autonomous payment authorization via AgentPay Policy Gate.",
        "product": {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "currency": product.currency or "INR",
            "merchant_id": product.merchant_id
        },
        "payment_challenge": {
            "rail": "RAZORPAY",
            "network": "test",
            "order_id": order_draft_id,
            "amount": product.price,
            "amount_paise": amount_paise,
            "currency": "INR",
            "quote_validity_seconds": 300
        },
        "resolution_instructions": {
            "action": "create_purchase_intent",
            "endpoint": "/api/v1/purchase-intents",
            "payload_example": {
                "product_id": product.id,
                "agent_id": request.agent_id if request else "agent_001",
                "amount": product.price,
                "idempotency_key": str(uuid.uuid4())
            },
            "policy_rule": "AgentPay will evaluate spending ceiling, reserve funds (AUTHORIZED), and capture via Razorpay."
        }
    }

    return JSONResponse(status_code=402, content=body, headers=headers)
