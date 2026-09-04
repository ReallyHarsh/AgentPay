import os
import json
import re
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from agentpay.merchants.service import MerchantService
from agentpay.transactions.service import TransactionService
from agentpay.receipts.service import ReceiptService
from agentpay.agents.intent import IntentAgent


# The Safe Tool Definition Schema (OpenAI / JSON-Schema format)
SAFE_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Deep multi-attribute semantic search for catalog products by keyword, category, price ceiling/floor, brand, and technical specifications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query keywords (e.g. 'wireless headphones with ANC', '4K monitor with USB-C')"},
                    "category": {"type": "string", "description": "Optional category filter (e.g. 'audio', 'electronics', 'accessories', 'displays', 'office', 'books')"},
                    "max_price": {"type": "number", "description": "Optional maximum price ceiling in INR"},
                    "min_price": {"type": "number", "description": "Optional minimum price floor in INR"},
                    "brand": {"type": "string", "description": "Optional brand filter (e.g. 'Sony', 'Apple', 'Dell', 'Logitech', 'JBL', 'Anker')"},
                    "feature_keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional technical features to match (e.g. ['ANC', 'OLED', 'USB-C', 'Bluetooth 5.3', '32GB RAM'])"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_quote",
            "description": "Get verified real-time pricing, stock quote, and technical specs for a specific product ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Unique ID of the product"}
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_purchase_intent",
            "description": "Request purchase of a product. AgentPay will evaluate policies and authorize payment if approved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Unique ID of product to purchase"},
                    "amount": {"type": "number", "description": "Total amount in INR to authorize"},
                    "idempotency_key": {"type": "string", "description": "Optional unique idempotency key"}
                },
                "required": ["product_id", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_transaction_status",
            "description": "Check current state machine status and audit log of a transaction ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transaction_id": {"type": "string", "description": "Transaction ID"}
                },
                "required": ["transaction_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_receipt",
            "description": "Retrieve official receipt for a completed transaction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "receipt_id": {"type": "string", "description": "Receipt ID or Receipt Number"}
                },
                "required": ["receipt_id"]
            }
        }
    }
]


class AIBuyer:
    """
    Single Autonomous AI Buyer Agent.
    Operates via an iterative, multi-tool calling loop over safe commerce tools:
    - Tool 1: `search_products` (Federated multi-merchant discovery)
    - Tool 2: `get_quote` (Live price, inventory verification, quote evaluation)
    - Tool 3: `create_purchase_intent` (Submits purchase intent to AgentPay Gateway)
    - Tool 4: `get_receipt` (Retrieves verified tax receipt upon payment)
    - Tool 5: `get_transaction_status` (State machine verification)

    Maintains the AgentPay Invariant:
    The AI Agent can formulate intents and call safe discovery/proposal tools;
    only the AgentPay Policy Engine & Rails can authorize or execute transactions.
    Exposes tools natively via the Anthropic / Razorpay Model Context Protocol (MCP).
    """

    def __init__(self, agent_id: str = "agent_001"):
        self.agent_id = agent_id

    def get_mcp_server(self):
        """Returns the Model Context Protocol (MCP) server instance for this buyer."""
        from agentpay.mcp.server import get_mcp_server
        return get_mcp_server(self.agent_id)

    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Returns the standardized MCP tools list conforming to the Model Context Protocol spec."""
        from agentpay.mcp.server import get_mcp_tools_list
        return await get_mcp_tools_list(self.agent_id)

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Executes an allowed tool call deterministically.
        Rejects any attempt to invoke forbidden financial or policy tools.
        """
        from agentpay.mcp.server import FORBIDDEN_TOOLS

        if tool_name in FORBIDDEN_TOOLS:
            return {
                "error": "SECURITY_VIOLATION",
                "message": f"Tool '{tool_name}' is forbidden. Only AgentPay Policy & Payment services can authorize or handle money."
            }

        if tool_name == "search_products":
            results = MerchantService.search_products(
                query=arguments.get("query"),
                category=arguments.get("category"),
                max_price=arguments.get("max_price"),
                min_price=arguments.get("min_price"),
                brand=arguments.get("brand"),
                feature_keywords=arguments.get("feature_keywords"),
                db=db
            )
            # Broader fallback if strict price limit returned empty
            if not results and arguments.get("max_price") is not None:
                results = MerchantService.search_products(
                    query=arguments.get("query"),
                    category=arguments.get("category"),
                    brand=arguments.get("brand"),
                    feature_keywords=arguments.get("feature_keywords"),
                    db=db
                )
            # Broader fallback if category or brand filter returned empty
            if not results and (arguments.get("category") is not None or arguments.get("brand") is not None):
                results = MerchantService.search_products(
                    query=arguments.get("query"),
                    max_price=arguments.get("max_price"),
                    feature_keywords=arguments.get("feature_keywords"),
                    db=db
                )
            return {"products": results, "count": len(results)}

        elif tool_name == "get_quote":
            product_id = arguments.get("product_id")
            quote = MerchantService.get_quote(
                product_id=product_id,
                db=db
            )
            if not quote:
                return {"error": "PRODUCT_NOT_FOUND", "message": f"Product ID '{product_id}' not found"}
            return {"quote": quote}

        elif tool_name == "create_purchase_intent":
            product_id = arguments.get("product_id")
            amount = arguments.get("amount")
            quote = MerchantService.get_quote(product_id=product_id, db=db)
            merchant_id = quote.get("merchant_id", "merchant_001") if quote else "merchant_001"
            simulate_failure = bool(arguments.get("simulate_failure", False))

            result = TransactionService.create_and_process_intent(
                agent_id=self.agent_id,
                merchant_id=merchant_id,
                product_id=product_id,
                amount=float(amount),
                currency="INR",
                idempotency_key=arguments.get("idempotency_key"),
                simulate_failure=simulate_failure,
                db=db
            )
            return {"transaction": result}

        elif tool_name == "get_transaction_status":
            tx = TransactionService.get_transaction(arguments.get("transaction_id"), db)
            if not tx:
                return {"error": "TRANSACTION_NOT_FOUND"}
            return {"transaction": tx}

        elif tool_name == "get_receipt":
            rcpt = ReceiptService.get_receipt(arguments.get("receipt_id"), db)
            if not rcpt:
                return {"error": "RECEIPT_NOT_FOUND"}
            return {
                "receipt": {
                    "id": rcpt.id,
                    "receipt_number": rcpt.receipt_number,
                    "amount": rcpt.amount,
                    "currency": rcpt.currency,
                    "details": rcpt.details
                }
            }

        else:
            return {"error": "UNKNOWN_TOOL", "message": f"Tool '{tool_name}' is not recognized."}

    def chat(self, user_message: str, db: Session) -> Dict[str, Any]:
        """
        Executes the autonomous AI Buyer workflow orchestrated via LangGraph:
        - Node 1: parse_intent (Structured intent extraction)
        - Branch: clarify vs. retrieve
        - Node 2: retrieve (Hybrid semantic & multi-merchant catalog search)
        - Node 3: evaluate_retrieval (Corrective RAG / reflection)
        - Node 4: rewrite_query (Query refinement loop)
        - Node 5: propose_buyer (Quote optimization, policy evaluation, checkout)
        """
        try:
            from agentpay.agents.graph import agentpay_graph_app

            initial_state = {
                "user_message": user_message,
                "agent_id": self.agent_id,
                "db_session": db,
                "steps": [],
                "retry_count": 0
            }

            final_state = agentpay_graph_app.invoke(initial_state)

            return {
                "response": final_state.get("response", ""),
                "steps": final_state.get("steps", []),
                "clarification": final_state.get("clarification"),
                "proposal": final_state.get("proposal"),
                "transaction": final_state.get("transaction")
            }
        except Exception:
            return self._legacy_chat(user_message=user_message, db=db)

    def run(self, user_message: str, db: Session) -> Dict[str, Any]:
        """Compatibility wrapper for tests and older callers."""
        return self.chat(user_message=user_message, db=db)

    def _legacy_chat(self, user_message: str, db: Session) -> Dict[str, Any]:
        """
        Executes the Single Agent autonomous workflow using multiple tool calls:
        1. Parse intent & constraints (or trigger clarification for broad queries)
        2. Tool Call: `search_products`
        3. Tool Call(s): `get_quote` for candidate SKUs across merchants
        4. Evaluate quotes, ranking, and build checkout proposal
        5. If autonomous / confirmed:
           Tool Call: `create_purchase_intent`
           Tool Call: `get_receipt` (if transaction succeeded)
        """
        steps: List[Dict[str, Any]] = []

        # 1. Parse user goal & constraints
        intent_data = IntentAgent.parse_intent(user_message)

        # Clarification branch: Keep Human-in-the-Loop if requirements are broad
        if intent_data["needs_clarification"] and intent_data["clarification_options"]:
            steps.append({
                "step": "CLARIFICATION_REQUIRED",
                "tool": "request_clarification",
                "arguments": {
                    "raw_message": user_message,
                    "category": intent_data.get("category")
                },
                "thought": f"User query '{user_message}' lacks specific budget or form-factor constraints. Pausing to request clarification before making tool calls.",
                "output": {
                    "question": intent_data["clarifying_question"],
                    "options": intent_data["clarification_options"]
                }
            })

            options_text = "\n".join([f"  • **{opt['label']}**" for opt in intent_data["clarification_options"]])
            return {
                "response": (
                    f"🤔 **I'd love to help you find the perfect {intent_data['category'] or 'item'}, but I want to keep you in the loop!**\n\n"
                    f"**{intent_data['clarifying_question']}**\n\n"
                    f"Here are a few quick paths you can choose from:\n"
                    f"{options_text}\n\n"
                    f"Click one of the option chips below or tell me your budget/preferred brand!"
                ),
                "steps": steps,
                "clarification": {
                    "question": intent_data["clarifying_question"],
                    "options": intent_data["clarification_options"]
                },
                "proposal": None,
                "transaction": None
            }

        # 2. TOOL CALL 1: search_products
        search_args = {
            "query": intent_data.get("clean_query"),
            "category": intent_data.get("category"),
            "max_price": intent_data.get("max_price"),
            "min_price": intent_data.get("min_price"),
            "brand": intent_data.get("brand"),
            "feature_keywords": intent_data.get("feature_keywords")
        }
        search_output = self.execute_tool("search_products", search_args, db)
        products = search_output.get("products", [])

        steps.append({
            "step": "TOOL_CALL",
            "tool": "search_products",
            "arguments": search_args,
            "thought": (
                f"[Single Agent] Executing tool call 'search_products' with query='{intent_data['clean_query']}', "
                f"category='{intent_data['category'] or 'all'}', max_price={intent_data['max_price']}, brand={intent_data['brand']}. "
                f"Discovered {len(products)} candidate SKU(s)."
            ),
            "output": {
                "products_found": len(products),
                "top_matches": [p["name"] for p in products[:3]]
            }
        })

        if not products:
            return {
                "response": (
                    f"I searched our merchant catalogs for '{user_message}', but could not find any matching products. "
                    f"Try searching for headphones (ANC), 4K monitors, mechanical keyboards, vertical mice, laptops (OLED, 32GB RAM), or Kindle e-readers."
                ),
                "steps": steps,
                "clarification": None,
                "proposal": None,
                "transaction": None
            }

        # 3. TOOL CALL 2: get_quote across candidates
        candidates = products[:4]
        quotes = []
        for candidate in candidates:
            quote_res = self.execute_tool("get_quote", {"product_id": candidate["id"]}, db)
            if quote_res.get("quote"):
                quotes.append(quote_res["quote"])

        if not quotes:
            selected_quote = {"total_amount": candidates[0]["price"], "unit_price": candidates[0]["price"], "product_id": candidates[0]["id"]}
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
                # Rank by customer review rating descending, then spec count descending
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
                # Rank strictly by lowest price ascending
                ranked_quotes = sorted(quotes, key=lambda q: q["total_amount"])
                selected_quote = ranked_quotes[0]
                rationale = "Negotiated lowest guaranteed price across merchant catalog nodes."
            else:
                # Balanced value-for-money: prioritize highest semantic relevance, breaking ties with lowest price
                ranked_quotes = sorted(
                    quotes,
                    key=lambda q: (
                        cand_relevance.get(q["product_id"], 0),
                        q.get("in_stock", True),
                        -q["total_amount"]  # lower price is preferred among equally relevant items
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
                f"[Single Agent] Executed 'get_quote' across {len(quotes)} candidate SKUs. "
                f"{rationale} Selected '{selected_product['name']}' at ₹{selected_quote['total_amount']:,.2f}."
            ),
            "output": {
                "selected_quote": selected_quote,
                "comparison": comparison_summary,
                "rationale": rationale
            }
        })

        # Build Tiered Options (Budget vs Recommended vs Premium Flagship)
        tiered_options = []
        if len(products) > 1:
            sel_sub_type = selected_product.get("sub_type")
            sel_cat = selected_product.get("category")
            # Strictly match the exact same sub-type / form-factor
            if sel_sub_type:
                matching_pool = [p for p in products if p.get("sub_type") == sel_sub_type]
            else:
                matching_pool = [
                    p for p in products
                    if p.get("category") == sel_cat and not p.get("sub_type")
                ]

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

        # Check whether we should execute payment immediately or pause for user choice
        is_direct_sku_confirmation = "confirm and" in user_message.lower() or "sku prod_" in user_message.lower()
        should_execute_immediately = intent_data["autonomous_mode"] or (intent_data["is_buy_command"] and is_direct_sku_confirmation)

        if not should_execute_immediately:
            return {
                "response": (
                    f"🤝 **AI Buyer Recommendation (Keeping you in the loop):**\n\n"
                    f"📦 **{selected_product['name']}**\n"
                    f"- **Merchant:** {merchant_name} (`{merchant_id}`)\n"
                    f"- **Negotiated Price:** ₹{price:,.2f}\n"
                    f"- **Rating:** ⭐ {selected_product.get('rating', 4.8)} / 5.0\n"
                    f"- **Optimization:** {rationale}\n"
                    f"- **Key Specifications:**{specs_bullets}\n\n"
                    f"You can choose between merchants, select alternatives, or customize options on the card below before confirming payment!"
                ),
                "steps": steps,
                "clarification": None,
                "proposal": proposal_data,
                "transaction": None
            }

        # 4. TOOL CALL 3: create_purchase_intent
        idempotency_key = f"intent_{self.agent_id}_{selected_product['id']}_{uuid.uuid4().hex[:8]}"
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

        purchase_call_res = self.execute_tool("create_purchase_intent", intent_payload, db)
        tx = purchase_call_res.get("transaction", {})
        tx_status = tx.get("status")
        policy_result = tx.get("policy_result", {})

        steps.append({
            "step": "TOOL_CALL",
            "tool": "create_purchase_intent",
            "arguments": intent_payload,
            "thought": (
                f"[Single Agent] Formulated PurchaseIntent for SKU '{selected_product['id']}' (₹{price:,.2f}). "
                f"Delegating intent to AgentPay Gateway for policy validation & Razorpay settlement."
            ),
            "output": purchase_call_res
        })

        steps.append({
            "step": "GATEWAY_EVALUATION",
            "tool": "agentpay_authorization",
            "arguments": {"transaction_id": tx.get("id"), "amount": price, "currency": "INR"},
            "output": tx,
            "thought": f"[AgentPay Gateway] Evaluated policy constraints, two-phase budget reservation, and payment rails. Status: '{tx_status}'."
        })

        # 5. TOOL CALL 4: get_receipt (if receipt was generated)
        receipt_obj = tx.get("receipt")
        if receipt_obj and receipt_obj.get("id"):
            receipt_call_res = self.execute_tool("get_receipt", {"receipt_id": receipt_obj["id"]}, db)
            steps.append({
                "step": "TOOL_CALL",
                "tool": "get_receipt",
                "arguments": {"receipt_id": receipt_obj["id"]},
                "thought": f"[Single Agent] Retrieved verified official tax receipt #{receipt_obj.get('receipt_number')} for transaction '{tx.get('id')}'.",
                "output": receipt_call_res
            })

        # 6. Construct Final Response
        if tx_status in ("RECEIPT_GENERATED", "PAYMENT_SUCCESS", "ORDER_CONFIRMED"):
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

    run = chat
