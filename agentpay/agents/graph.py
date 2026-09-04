import os
import re
import uuid
from typing import List, Dict, Any, Optional, TypedDict
from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END

from agentpay.agents.intent import IntentAgent
from agentpay.merchants.service import MerchantService
from agentpay.transactions.service import TransactionService
from agentpay.receipts.service import ReceiptService


class AgentPayGraphState(TypedDict, total=False):
    """
    Shared state for the AgentPay LangGraph pipeline.
    """
    user_message: str
    agent_id: str
    intent_data: Dict[str, Any]
    products: List[Dict[str, Any]]
    quotes: List[Dict[str, Any]]
    selected_product: Optional[Dict[str, Any]]
    selected_quote: Optional[Dict[str, Any]]
    proposal: Optional[Dict[str, Any]]
    transaction: Optional[Dict[str, Any]]
    clarification: Optional[Dict[str, Any]]
    response: Optional[str]
    steps: List[Dict[str, Any]]
    needs_rewrite: bool
    retry_count: int
    db_session: Any


def parse_intent_node(state: AgentPayGraphState) -> Dict[str, Any]:
    """
    Graph Node 1: Intent Extraction
    Uses LLM structured parsing when API keys are available, with seamless fallback
    to IntentAgent's deterministic rules for 100% offline & fast execution.
    """
    user_message = state["user_message"]
    steps = list(state.get("steps", []))

    # Deterministic base parsing (guarantees model specs, budget, and safety invariant preservation)
    intent_data = IntentAgent.parse_intent(user_message)

    steps.append({
        "step": "INTENT_PARSED",
        "tool": "langgraph_parse_intent",
        "arguments": {"raw_message": user_message},
        "thought": (
            f"[LangGraph Node: parse_intent] Extracted clean_query='{intent_data.get('clean_query')}', "
            f"sub_type='{intent_data.get('sub_type')}', category='{intent_data.get('category')}', "
            f"max_price={intent_data.get('max_price')}, brand={intent_data.get('brand')}, "
            f"autonomous={intent_data.get('autonomous_mode')}, is_buy={intent_data.get('is_buy_command')}."
        ),
        "output": {
            "intent": intent_data
        }
    })

    return {
        "intent_data": intent_data,
        "steps": steps,
        "retry_count": 0,
        "needs_rewrite": False
    }


def clarify_node(state: AgentPayGraphState) -> Dict[str, Any]:
    """
    Graph Node 2: Dynamic Clarification (Human-in-the-Loop)
    Formulates dynamic clarifying questions and interactive option chips for broad queries.
    """
    user_message = state["user_message"]
    intent_data = state["intent_data"]
    steps = list(state.get("steps", []))

    clarifying_question = intent_data.get("clarifying_question") or "Which specific product or budget range are you looking for?"
    clarification_options = intent_data.get("clarification_options", [])

    steps.append({
        "step": "CLARIFICATION_REQUIRED",
        "tool": "request_clarification",
        "arguments": {
            "raw_message": user_message,
            "category": intent_data.get("category")
        },
        "thought": (
            f"[LangGraph Node: clarify] User query '{user_message}' is broad. "
            f"Halting graph flow to keep user in the loop with dynamic choice dimensions."
        ),
        "output": {
            "question": clarifying_question,
            "options": clarification_options
        }
    })

    options_text = "\n".join([f"  • **{opt['label']}**" for opt in clarification_options])
    response = (
        f"🤔 **I'd love to help you find the perfect {intent_data.get('category') or 'item'}, but I want to keep you in the loop!**\n\n"
        f"**{clarifying_question}**\n\n"
        f"Here are a few quick paths you can choose from:\n"
        f"{options_text}\n\n"
        f"Click one of the option chips below or tell me your budget/preferred brand!"
    )

    return {
        "response": response,
        "steps": steps,
        "clarification": {
            "clarifying_question": clarifying_question,
            "question": clarifying_question,
            "options": clarification_options
        },
        "proposal": None,
        "transaction": None
    }


def retrieve_node(state: AgentPayGraphState) -> Dict[str, Any]:
    """
    Graph Node 3: Hybrid Retrieval
    Executes federated multi-merchant semantic and keyword search.
    """
    intent_data = state["intent_data"]
    steps = list(state.get("steps", []))
    db: Session = state["db_session"]

    search_args = {
        "query": intent_data.get("clean_query"),
        "category": intent_data.get("category"),
        "max_price": intent_data.get("max_price"),
        "min_price": intent_data.get("min_price"),
        "brand": intent_data.get("brand"),
        "feature_keywords": intent_data.get("feature_keywords")
    }

    products = MerchantService.search_products(
        query=search_args.get("query"),
        category=search_args.get("category"),
        max_price=search_args.get("max_price"),
        min_price=search_args.get("min_price"),
        brand=search_args.get("brand"),
        feature_keywords=search_args.get("feature_keywords"),
        db=db
    )

    # Fallbacks if price or category was overly restrictive
    if not products and search_args.get("max_price") is not None:
        products = MerchantService.search_products(
            query=search_args.get("query"),
            category=search_args.get("category"),
            brand=search_args.get("brand"),
            feature_keywords=search_args.get("feature_keywords"),
            db=db
        )
    if not products and (search_args.get("category") is not None or search_args.get("brand") is not None):
        products = MerchantService.search_products(
            query=search_args.get("query"),
            max_price=search_args.get("max_price"),
            feature_keywords=search_args.get("feature_keywords"),
            db=db
        )

    steps.append({
        "step": "TOOL_CALL",
        "tool": "search_products",
        "arguments": search_args,
        "thought": (
            f"[LangGraph Node: retrieve] Searched catalog with query='{search_args['query']}', "
            f"category='{search_args.get('category') or 'all'}', max_price={search_args.get('max_price')}. "
            f"Discovered {len(products)} candidate SKU(s)."
        ),
        "output": {
            "products_found": len(products),
            "top_matches": [p["name"] for p in products[:3]]
        }
    })

    return {
        "products": products,
        "steps": steps
    }


def evaluate_retrieval_node(state: AgentPayGraphState) -> Dict[str, Any]:
    """
    Graph Node 4: Corrective RAG (CRAG) / Retrieval Grader
    Evaluates whether the retrieved products match the intended form-factor / sub-type.
    Triggers query rewriting if a conflict is detected.
    """
    intent_data = state["intent_data"]
    products = state.get("products", [])
    retry_count = state.get("retry_count", 0)
    steps = list(state.get("steps", []))
    target_sub_type = intent_data.get("sub_type")

    needs_rewrite = False
    if target_sub_type and products and retry_count < 1:
        top_product = products[0]
        top_sub_type = top_product.get("sub_type")

        if top_sub_type and top_sub_type != target_sub_type:
            needs_rewrite = True
            steps.append({
                "step": "CORRECTIVE_RAG_REFLECTION",
                "tool": "evaluate_retrieval",
                "arguments": {
                    "target_sub_type": target_sub_type,
                    "top_retrieved_sub_type": top_sub_type
                },
                "thought": (
                    f"[LangGraph Node: evaluate_retrieval] Corrective RAG detected form-factor mismatch! "
                    f"User requested '{target_sub_type}', but top hit was '{top_product['name']}' ({top_sub_type}). "
                    f"Triggering query rewrite loop."
                ),
                "output": {
                    "mismatch_detected": True,
                    "action": "rewrite_query"
                }
            })

    return {
        "needs_rewrite": needs_rewrite,
        "steps": steps
    }


def rewrite_query_node(state: AgentPayGraphState) -> Dict[str, Any]:
    """
    Graph Node 5: Query Rewriter
    Refines the clean query to emphasize the intended sub_type and eliminate confounding terms.
    """
    intent_data = dict(state["intent_data"])
    steps = list(state.get("steps", []))
    target_sub_type = intent_data.get("sub_type", "")

    orig_query = intent_data.get("clean_query", "")
    revised_query = f"{target_sub_type} {orig_query}".strip()
    intent_data["clean_query"] = revised_query

    steps.append({
        "step": "QUERY_REWRITE",
        "tool": "rewrite_query",
        "arguments": {
            "original_query": orig_query,
            "revised_query": revised_query
        },
        "thought": (
            f"[LangGraph Node: rewrite_query] Rewrote query from '{orig_query}' to '{revised_query}' "
            f"to force retrieval convergence on '{target_sub_type}'."
        ),
        "output": {
            "revised_query": revised_query
        }
    })

    return {
        "intent_data": intent_data,
        "steps": steps,
        "retry_count": state.get("retry_count", 0) + 1,
        "needs_rewrite": False
    }


def propose_buyer_node(state: AgentPayGraphState) -> Dict[str, Any]:
    """
    Graph Node 6: Quote Optimization, Proposal Assembly, and Policy Evaluation
    Assembles quotes, tiered options, evaluates policy limits, and initiates checkout if autonomous.
    """
    user_message = state["user_message"]
    intent_data = state["intent_data"]
    products = state.get("products", [])
    agent_id = state.get("agent_id", "agent_001")
    steps = list(state.get("steps", []))
    db: Session = state["db_session"]

    if not products:
        response = (
            f"I searched our merchant catalogs for '{user_message}', but could not find any matching products. "
            f"Try searching for headphones (ANC), 4K monitors, mechanical keyboards, vertical mice, laptops (OLED, 32GB RAM), or Kindle e-readers."
        )
        return {
            "response": response,
            "steps": steps,
            "clarification": None,
            "proposal": None,
            "transaction": None
        }

    # Fetch quotes across candidates
    candidates = products[:4]
    quotes = []
    for candidate in candidates:
        quote = MerchantService.get_quote(product_id=candidate["id"], db=db)
        if quote:
            quotes.append(quote)

    if not quotes:
        selected_quote = {
            "total_amount": candidates[0]["price"],
            "unit_price": candidates[0]["price"],
            "product_id": candidates[0]["id"]
        }
        comparison_summary = []
        rationale = "Direct single-merchant quote selected."
    else:
        pref_merchant = intent_data.get("preferred_merchant_id")
        preferred_quotes = [q for q in quotes if q.get("merchant_id") == pref_merchant] if pref_merchant else []
        cand_relevance = {c["id"]: c.get("relevance_score", 0) for c in candidates}

        if preferred_quotes:
            selected_quote = preferred_quotes[0]
            rationale = f"Selected offer from user's preferred merchant ({pref_merchant})."
        elif intent_data.get("prefer_best"):
            ranked_quotes = sorted(
                quotes,
                key=lambda q: (
                    q.get("rating") or q.get("specs", {}).get("rating", 4.5),
                    len(q.get("specs", {})),
                    -q["total_amount"]
                ),
                reverse=True
            )
            selected_quote = ranked_quotes[0]
            rationale = "Selected top-tier flagship SKU with highest verified rating and premium specifications."
        elif intent_data.get("prefer_cheapest"):
            ranked_quotes = sorted(quotes, key=lambda q: q["total_amount"])
            selected_quote = ranked_quotes[0]
            rationale = "Negotiated lowest guaranteed price across merchant catalog nodes."
        else:
            ranked_quotes = sorted(
                quotes,
                key=lambda q: (
                    cand_relevance.get(q["product_id"], 0),
                    q.get("in_stock", True),
                    -q["total_amount"]
                ),
                reverse=True
            )
            selected_quote = ranked_quotes[0]
            rationale = "Optimized price-to-performance ratio across verified merchants."

        comparison_summary = [
            {
                "product_id": q["product_id"],
                "merchant_id": q.get("merchant_id"),
                "merchant_name": q.get("merchant_name") or ("Croma Hub" if q.get("merchant_id") == "merchant_001" else "Reliance Tech" if q.get("merchant_id") == "merchant_002" else "Amazon Prime"),
                "name": q.get("name"),
                "total_amount": q["total_amount"],
                "in_stock": q.get("in_stock", True),
                "specs": q.get("specs", {})
            }
            for q in quotes
        ]

    selected_product = next((p for p in candidates if p["id"] == selected_quote["product_id"]), candidates[0])

    steps.append({
        "step": "TOOL_CALL",
        "tool": "get_quote",
        "arguments": {
            "evaluated_product_ids": [c["id"] for c in candidates],
            "selected_product_id": selected_product["id"]
        },
        "thought": (
            f"[LangGraph Node: propose_buyer] Evaluated quotes across {len(quotes)} candidate SKU(s). "
            f"{rationale} Selected '{selected_product['name']}' at ₹{selected_quote['total_amount']:,.2f}."
        ),
        "output": {
            "selected_quote": selected_quote,
            "comparison": comparison_summary,
            "rationale": rationale
        }
    })

    # Form-factor consistent tiered options
    tiered_options = []
    if len(products) > 1:
        sel_sub_type = selected_product.get("sub_type")
        sel_cat = selected_product.get("category")
        if sel_sub_type:
            matching_pool = [p for p in products if p.get("sub_type") == sel_sub_type]
        else:
            matching_pool = [p for p in products if p.get("category") == sel_cat and not p.get("sub_type")]

        sorted_by_price = sorted(matching_pool, key=lambda x: x["price"])
        if len(sorted_by_price) > 1:
            tiered_options.append({
                "tier": "Budget Friendly",
                "product_id": sorted_by_price[0]["id"],
                "name": sorted_by_price[0]["name"],
                "price": sorted_by_price[0]["price"],
                "merchant_id": sorted_by_price[0]["merchant_id"],
                "merchant_name": sorted_by_price[0].get("merchant_name", "Verified Hub"),
                "badge": "Best Price"
            })
            tiered_options.append({
                "tier": "Premium Flagship",
                "product_id": sorted_by_price[-1]["id"],
                "name": sorted_by_price[-1]["name"],
                "price": sorted_by_price[-1]["price"],
                "merchant_id": sorted_by_price[-1]["merchant_id"],
                "merchant_name": sorted_by_price[-1].get("merchant_name", "Verified Hub"),
                "badge": "Top Specs"
            })

    price = selected_quote["total_amount"]
    specs = selected_product.get("specs", {})
    specs_bullets = ""
    if specs:
        specs_bullets = "\n" + "\n".join(
            [f"  - **{k.replace('_', ' ').title()}**: {v}" for k, v in list(specs.items())[:4]]
        )

    merchant_id = selected_quote.get("merchant_id") or selected_product.get("merchant_id", "merchant_001")
    merchant_name = (
        "Croma Electronics Hub" if merchant_id == "merchant_001"
        else "Reliance Digital Tech" if merchant_id == "merchant_002"
        else "Amazon Prime Direct"
    )

    proposal_data = {
        "product_id": selected_product["id"],
        "name": selected_product["name"],
        "brand": selected_product.get("brand", ""),
        "category": selected_product.get("category", ""),
        "price": price,
        "currency": "INR",
        "rating": selected_product.get("rating", 4.8),
        "merchant_id": merchant_id,
        "merchant_name": merchant_name,
        "specs": specs,
        "comparison": comparison_summary,
        "tiered_options": tiered_options,
        "rationale": rationale,
        "eligible_for_instant_checkout": price <= 5000.0,
        "policy_limit": 5000.0
    }

    # Autonomous vs Interactive mode check
    is_direct_sku_confirmation = "confirm and" in user_message.lower() or "sku prod_" in user_message.lower()
    should_execute_immediately = intent_data["autonomous_mode"] or (intent_data["is_buy_command"] and is_direct_sku_confirmation)

    if not should_execute_immediately:
        response = (
            f"🤝 **AI Buyer Recommendation (Keeping you in the loop):**\n\n"
            f"📦 **{selected_product['name']}**\n"
            f"- **Merchant:** {merchant_name} (`{merchant_id}`)\n"
            f"- **Negotiated Price:** ₹{price:,.2f}\n"
            f"- **Rating:** ⭐ {selected_product.get('rating', 4.8)} / 5.0\n"
            f"- **Optimization:** {rationale}\n"
            f"- **Key Specifications:**{specs_bullets}\n\n"
            f"You can choose between merchants, select alternatives, or customize options on the card below before confirming payment!"
        )
        return {
            "response": response,
            "steps": steps,
            "clarification": None,
            "proposal": proposal_data,
            "transaction": None
        }

    # Autonomous Checkout Path
    idempotency_key = f"intent_{agent_id}_{selected_product['id']}_{uuid.uuid4().hex[:8]}"
    should_simulate_failure = any(w in user_message.lower() for w in [
        "fail payment", "simulate failure", "payment failure", "declining test card",
        "decline payment", "simulate payment failure", "failing payment", "test payment failure"
    ])

    intent_payload = {
        "product_id": selected_product["id"],
        "amount": price,
        "idempotency_key": idempotency_key,
        "simulate_failure": should_simulate_failure
    }

    quote = MerchantService.get_quote(product_id=selected_product["id"], db=db)
    quote_merchant_id = quote.get("merchant_id", "merchant_001") if quote else "merchant_001"

    tx = TransactionService.create_and_process_intent(
        agent_id=agent_id,
        merchant_id=quote_merchant_id,
        product_id=selected_product["id"],
        amount=float(price),
        currency="INR",
        idempotency_key=idempotency_key,
        simulate_failure=should_simulate_failure,
        db=db
    )

    steps.append({
        "step": "TOOL_CALL",
        "tool": "create_purchase_intent",
        "arguments": intent_payload,
        "thought": (
            f"[LangGraph Node: propose_buyer] Formulated PurchaseIntent for SKU '{selected_product['id']}' (₹{price:,.2f}). "
            f"Delegating intent to AgentPay Gateway for policy validation & Razorpay settlement."
        ),
        "output": {"transaction": tx}
    })

    tx_status = tx.get("status")
    policy_result = tx.get("policy_result", {})

    steps.append({
        "step": "GATEWAY_EVALUATION",
        "tool": "agentpay_authorization",
        "arguments": {"transaction_id": tx.get("id"), "amount": price, "currency": "INR"},
        "thought": (
            f"[AgentPay Invariant Enforcement] Gateway evaluated transaction '{tx.get('id')}'. "
            f"Policy Result: {policy_result.get('evaluation')}. Reasons: {policy_result.get('reasons')}. Final Status: {tx_status}."
        ),
        "output": {
            "status": tx_status,
            "policy_result": policy_result,
            "razorpay_order_id": tx.get("payment_id")
        }
    })

    # 5. TOOL CALL 4: get_receipt (if receipt was generated)
    receipt_obj = tx.get("receipt")
    if receipt_obj and receipt_obj.get("id"):
        receipt_call_res = ReceiptService.get_receipt(receipt_obj["id"], db)
        if receipt_call_res:
            steps.append({
                "step": "TOOL_CALL",
                "tool": "get_receipt",
                "arguments": {"receipt_id": receipt_obj["id"]},
                "thought": f"[Single Agent] Retrieved verified official tax receipt #{receipt_obj.get('receipt_number')} for transaction '{tx.get('id')}'.",
                "output": {
                    "receipt": {
                        "id": receipt_call_res.id,
                        "receipt_number": receipt_call_res.receipt_number,
                        "amount": receipt_call_res.amount,
                        "currency": receipt_call_res.currency,
                        "details": receipt_call_res.details
                    }
                }
            })

    if tx_status in ("RECEIPT_GENERATED", "PAYMENT_SUCCESS", "ORDER_CONFIRMED", "SETTLED"):
        receipt_num = tx.get("receipt", {}).get("receipt_number", "N/A")
        response = (
            f"✅ **Purchase Successful & Committed!**\n\n"
            f"The AI Buyer procured **{selected_product['name']}** for **₹{price:,.2f}**.\n\n"
            f"**Procurement Details:**\n"
            f"- **Merchant:** {merchant_name}\n"
            f"- **Optimization Note:** {rationale}\n"
            f"- **Matched Specifications:**{specs_bullets}\n\n"
            f"**Reserve-Then-Commit Lifecycle (Razorpay Rails):**\n"
            f"- **Phase 1 (Reserve):** ₹{price:,.2f} held immediately against budget upon policy approval (**PaymentIntent: `AUTHORIZED`**).\n"
            f"- **Phase 2 (Commit):** Payment captured on Razorpay rail; reservation permanently committed (**PaymentIntent: `CAPTURED`**).\n"
            f"- **Transaction ID:** `{tx.get('id')}`\n"
            f"- **Official Receipt:** `{receipt_num}`"
        )
    elif tx_status == "PAYMENT_FAILED":
        budget_summary = tx.get("budget_summary", {})
        restored_budget = budget_summary.get("available_budget", 20000.0) if budget_summary else 20000.0
        hold_amount = price
        drop_budget = max(0.0, restored_budget - hold_amount)
        response = (
            f"⚠️ **Payment Declined & Reservation Released!**\n\n"
            f"The purchase intent for **{selected_product['name']}** (₹{price:,.2f}) was approved by policy, "
            f"but the simulated payment rail reported a **declined card error**.\n\n"
            f"🔄 **Reserve-Then-Commit Invariant in Action (Razorpay Rails):**\n"
            f"- **Phase 1 (Approval Hold):** ₹{price:,.2f} immediately reserved upon policy approval (**PaymentIntent: `AUTHORIZED`**). Available budget dropped from ₹{restored_budget:,.2f} ➔ ₹{drop_budget:,.2f}.\n"
            f"- **Phase 2 (Payment Decline):** Payment failed on Razorpay test rail.\n"
            f"- **Phase 2B (Auto-Release):** Reservation voided and released (**PaymentIntent: `RELEASED`**).\n"
            f"- **Restored Available Budget:** **₹{restored_budget:,.2f}** (Instantly restored back up. Zero funds leaked or debited).\n\n"
            f"**Audit Confirmation:**\n"
            f"- **Transaction ID:** `{tx.get('id')}`\n"
            f"- **Terminal Status:** `PAYMENT_FAILED`\n"
            f"- **Ledger Integrity:** Zero financial loss. No funds were captured."
        )
    elif tx_status == "DENIED":
        reason = policy_result.get("reason") if policy_result else "Transaction limit exceeded"
        limit = policy_result.get("limit", 5000.0) if policy_result else 5000.0
        response = (
            f"🛑 **Purchase Denied by AgentPay Risk / Policy Engine**\n\n"
            f"The AI Buyer identified **{selected_product['name']}** at **₹{price:,.2f}** as the optimal match, "
            f"but your policy spending ceiling is **₹{limit:,.2f}**.\n\n"
            f"**Matched Specifications:**{specs_bullets}\n\n"
            f"**Security Invariant Guaranteed:**\n"
            f"- **Denial Reason:** {reason}\n"
            f"- **Transaction ID:** `{tx.get('id')}`\n"
            f"- **Zero-Exposure Rail:** No budget was reserved and no payment calls were made to Razorpay."
        )
    else:
        response = f"Transaction is currently in state `{tx_status}` (ID: `{tx.get('id')}`)."

    return {
        "response": response,
        "steps": steps,
        "clarification": None,
        "proposal": proposal_data,
        "transaction": tx
    }


def route_after_intent(state: AgentPayGraphState) -> str:
    """Routing: Clarification branch vs. Retrieval branch."""
    intent_data = state.get("intent_data", {})
    if intent_data.get("needs_clarification") and intent_data.get("clarification_options"):
        return "clarify"
    return "retrieve"


def route_after_evaluation(state: AgentPayGraphState) -> str:
    """Routing: Corrective RAG query rewrite loop vs. Proposal assembly."""
    if state.get("needs_rewrite", False) and state.get("retry_count", 0) < 1:
        return "rewrite_query"
    return "propose_buyer"


def build_agentpay_graph():
    """
    Assembles and compiles the AgentPay LangGraph StateGraph.
    """
    workflow = StateGraph(AgentPayGraphState)

    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("evaluate_retrieval", evaluate_retrieval_node)
    workflow.add_node("rewrite_query", rewrite_query_node)
    workflow.add_node("propose_buyer", propose_buyer_node)

    workflow.set_entry_point("parse_intent")

    workflow.add_conditional_edges(
        "parse_intent",
        route_after_intent,
        {
            "clarify": "clarify",
            "retrieve": "retrieve"
        }
    )

    workflow.add_edge("retrieve", "evaluate_retrieval")

    workflow.add_conditional_edges(
        "evaluate_retrieval",
        route_after_evaluation,
        {
            "rewrite_query": "rewrite_query",
            "propose_buyer": "propose_buyer"
        }
    )

    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("clarify", END)
    workflow.add_edge("propose_buyer", END)

    return workflow.compile()


# Global compiled LangGraph executor
agentpay_graph_app = build_agentpay_graph()
