# AgentPay Specification & Threat Model

**Project:** AgentPay (Autonomous AI Commerce Payment-Control Layer)  
**Version:** 1.0.0 (Hackathon MVP)  
**Core Proof Point:** *The AI can decide, only AgentPay can authorize money.*

---

## 1. Security Architecture & Threat Model

### The Fundamental Risk of Agentic Commerce
In human-facing ecommerce, the checkout boundary is naturally enforced by user presence (entering OTP, CVV, clicking "Pay"). When an LLM acts autonomously on behalf of a user, malicious prompts, hallucination, or adversarial price gouging can trick the agent into overspending or draining funds.

### The AgentPay Invariant
```
+------------------+         Intent           +--------------------+
|     AI Buyer     | -----------------------> |  AgentPay Backend  |
| (LLM + Tool-Set) |                          |   (Policy Engine)  |
+------------------+                          +--------------------+
         |                                               |
         X (BLOCKED)                                     | Evaluates Limits
         |                                               v
+------------------+                          +--------------------+
|  Payment Rails   | <======================= |   RazorpayAdapter  |
|    (Razorpay)    |        Authorized        +--------------------+
+------------------+
```

1. **Explicit Safe Toolset:**
   - `search_products(query)`
   - `get_quote(product_id)`
   - `create_purchase_intent(product_id, amount)`
   - `get_transaction_status(transaction_id)`
   - `get_receipt(receipt_id)`

2. **Never Exposed Tools (Structural Security Boundary):**
   - `charge_card`
   - `transfer_money`
   - `modify_policy`
   - `modify_limits`
   - `access_payment_credentials`

Because these functions do not exist in the LLM's tool definition schema, no prompt injection or jailbreak can invoke money movement directly.

---

## 2. Transaction State Machine

```
CREATED
  │
  ▼
POLICY_CHECKED
  ├──────────────────────────────────┐
  │ APPROVED                         │ DENIED (Terminal)
  ▼                                  ▼
PAYMENT_CREATED                 [No payment ever attempted]
  ├──────────────┐
  │ SUCCESS      │ FAILED
  ▼              ▼
PAYMENT_SUCCESS  PAYMENT_FAILED (Terminal)
  │
  ▼
ORDER_CONFIRMED
  │
  ▼
RECEIPT_GENERATED (Final)
```

Every transition appends an immutable record to the `audit_events` table with:
- `transaction_id`
- `event_type`
- `actor_type` (`AI_BUYER`, `POLICY_ENGINE`, `PAYMENT_SERVICE`, `MERCHANT_SERVICE`, `SYSTEM`)
- `metadata` (JSON snapshot of context and payload)
- `created_at` (UTC timestamp)

---

## 3. Data Schema

| Entity | Purpose |
|---|---|
| `agents` | AI Buyer entities registered to the system |
| `agent_policies` | Spending limits (per-transaction), allowed categories, blocked merchants |
| `merchants` | Verified internal or external sellers |
| `products` | Merchant catalog items with categories, prices, and stock |
| `purchase_intents` | AI Buyer's requested purchase intent with idempotency keys |
| `payment_intents` | Payment authorization entity linked to Razorpay |
| `transactions` | State machine tracking orchestrator |
| `audit_events` | Immutable 7-stage event log trail |
| `receipts` | Official itemized receipt records |

---

## 4. API Endpoints

- `POST /api/v1/purchase-intents` — AI Buyer initiates purchase
- `POST /api/v1/policies/evaluate` — Deterministic policy verification
- `POST /api/v1/payment-intents` — Authorized payment creation
- `GET  /api/v1/transactions/:id` — State machine and audit trail polling
- `GET  /api/v1/receipts/:id` — Receipt retrieval
- `GET  /api/v1/products` — Catalog discovery
- `GET/PUT /api/v1/agents/:id/policy` — Policy configuration
- `POST /api/v1/chat` — AI Buyer conversational interface with step-by-step trace
