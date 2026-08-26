# AgentPay

**AI Buyer → Merchant, with policy-controlled autonomous payment.**

AgentPay is a trust and payment-control layer for autonomous AI commerce. An AI Buyer
can discover products, evaluate offers, and request a purchase — but it can never
authorize money movement on its own. That boundary is owned entirely by AgentPay.

> The AI can request a payment. It cannot independently authorize or control money.

---

## Why this exists

Traditional checkout assumes a human is present to click "buy." Agentic commerce
removes that human from the loop — which means something else has to own spending
limits, risk checks, and payment execution. AgentPay is that layer: a deterministic
policy engine sitting between an LLM's *decision* and a real payment provider's
*execution*.

---

## Demo

Two scenarios prove the system end to end.

**1. Approved purchase**
```
User:  "Buy good wireless headphones under ₹5,000."
AI:     searches products → selects JBL Tune 770NC (₹4,499)
        → creates purchase intent
Policy: ₹4,499 ≤ ₹5,000 limit, category allowed, merchant allowed → APPROVED
Payment: Razorpay test payment → SUCCESS
Result: order confirmed, receipt generated, full audit trail shown
```

**2. Denied purchase — the important one**
```
User:  "Buy the best laptop you can find."
AI:     finds a laptop at ₹85,000 → creates purchase intent
Policy: ₹85,000 > ₹5,000 limit → DENIED (TRANSACTION_LIMIT_EXCEEDED)
Result: no payment is ever attempted
AI:    "I found a laptop at ₹85,000, but your limit is ₹5,000,
        so I did not purchase it."
```

The second scenario is the actual proof of concept: the AI *tried* to overspend, and
the system stopped it before any payment call was made.

---

## Architecture

```
AI DECISION → USER POLICY → RISK CHECK → FINANCIAL AUTHORIZATION → PAYMENT → SETTLEMENT
```

```
User → AI Buyer (LLM + tool calling)
           │  create_purchase_intent
           ▼
      Backend API (FastAPI)
           │
           ▼
      Policy Engine  ──DENIED──▶  stop, no payment call made
           │ APPROVED
           ▼
      Payment Service (RazorpayAdapter)
           │
           ▼
      Razorpay Test Mode
           │
           ▼
      Transaction + Audit Log → Receipt
```

The AI Buyer's tool set is the actual security boundary — not a prompt instruction:

```
Exposed to the LLM:      search_products, get_quote, create_purchase_intent,
                          get_transaction_status, get_receipt

Never exposed to the LLM: charge_card, transfer_money, modify_policy,
                          modify_limits, access_payment_credentials
```

Since none of the money-moving functions exist as callable tools, the LLM has no path
to authorize a payment on its own, regardless of what it's asked or how it's prompted.

---

## Tech stack

| Layer      | Choice                                   |
|------------|-------------------------------------------|
| Frontend   | Next.js, React, Tailwind CSS              |
| Backend    | Python, FastAPI, Pydantic, SQLAlchemy     |
| Database   | SQLite                                    |
| AI         | LLM with function/tool calling            |
| Payments   | Razorpay (test mode)                      |

---

## Project structure

```
agentpay/
├── apps/
│   ├── api/                 # FastAPI app + routes
│   └── web/                 # Next.js frontend (chat, timeline, policy views)
├── agentpay/                 # core domain package
│   ├── agents/buyer.py        # LLM tool-calling loop
│   ├── policy/engine.py       # amount / category / merchant checks
│   ├── payments/
│   │   ├── service.py
│   │   └── razorpay.py        # RazorpayAdapter
│   ├── merchants/service.py   # seeded product catalog
│   ├── transactions/
│   │   ├── service.py
│   │   └── state_machine.py
│   ├── receipts/service.py
│   └── database/
├── tests/
├── docs/
│   └── spec.md                # full product/technical spec
└── README.md
```

---

## Getting started

```bash
# clone
git clone <repo-url>
cd agentpay

# backend
cd apps/api
pip install -r requirements.txt
cp .env.example .env          # add RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET (test mode) and LLM API key
uvicorn main:app --reload

# frontend
cd ../web
npm install
npm run dev
```

Visit `http://localhost:3000` and start a chat with the AI Buyer.

### Environment variables

```
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
LLM_API_KEY=
DATABASE_URL=sqlite:///./agentpay.db
```

---

## What's in scope for this build

- Purchase Intent → Policy Engine → Payment Intent → Razorpay test payment → Receipt
- Deterministic policy checks: per-transaction limit, allowed categories, blocked merchants
- Full audit event log for every state transition
- Idempotency keys on purchase and payment creation
- Real LLM tool-calling, restricted to a safe, explicit tool set
- Chat view + transaction timeline view + a static policy dashboard

## What's explicitly out of scope (and why)

| Cut                                   | Reason                                                          |
|----------------------------------------|------------------------------------------------------------------|
| Risk Engine as a separate module       | Folded into the policy check — not the differentiator being tested |
| Webhooks + signature verification      | Synchronous status polling instead — same guarantee, less infra   |
| Daily spending limit enforcement       | Field exists in the schema; not enforced in this build            |
| Merchant Dashboard UI                  | Doesn't touch the core authorization story                        |
| Multiple/live merchant discovery       | One internal merchant, seeded with realistic product data         |
| Postgres / Docker / Kubernetes         | SQLite, single process — sufficient for the demo                  |
| Real checkout on live shopping sites   | Would break the whole premise: AgentPay has to own the payment execution boundary, which isn't possible on third-party checkout flows |

These are scope decisions, not gaps — the goal of this build is to prove the
authorization boundary works, not to replicate a production commerce platform.

---

## Roadmap (not built, documented for context)

- V2: AI-to-AI negotiation, merchant onboarding, refunds, subscriptions
- V3: agent/merchant reputation, cryptographic agent identity, signed receipts
- V4: multi-payment-provider routing, agent commerce protocol, autonomous procurement

---

## License

TBD
