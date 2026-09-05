# AgentPay — System Architecture Diagram

> **Core Invariant:** *The AI can decide. Only AgentPay can authorize money.*

---

## 1. High-Level System Architecture

```mermaid
flowchart TB
    subgraph UL["👤 User Layer"]
        USER(["User"])
        WEB["Next.js Web App<br/>localhost:3000"]
    end

    subgraph AI["🧠 AI Buyer Layer"]
        LLM["LLM (Gemini/OpenAI)<br/>Tool-Calling Loop"]
        MCP["MCP Server<br/>stdio / SSE"]
        LANG["LangGraph Pipeline<br/>6 Nodes"]
    end

    subgraph GW["🛡️ AgentPay Gateway (FastAPI :8000)"]
        CHAT["Chat Router<br/>POST /api/v1/chat"]
        PI["Purchase Intents Router"]
        PM["Payments Router"]
        TX["Transactions Router"]
        PR["Products Router"]
        PL["Policies Router"]
        RC["Receipts Router"]
        MCP_R["MCP Router<br/>/api/v1/mcp/*"]
        WH["Webhooks Router"]
    end

    subgraph DOM["📦 Domain Engine"]
        INTENT["Intent Agent<br/>NLP / Constraints"]
        PRODUCT["Product Agent<br/>Semantic Retrieval"]
        NEG["Negotiation Agent<br/>Quote Comparison"]
        PAY["Payment Agent<br/>Intent Assembly"]
        POL["Policy Engine<br/>4 Deterministic Rules"]
        SM["State Machine<br/>9 States"]
        TXS["Transaction Service<br/>2-Phase Reserve-Commit"]
        PMT["Payment Service<br/>Reserve / Commit / Release"]
        RZR["Razorpay Adapter<br/>Sandbox / Live"]
        RCP["Receipt Service"]
    end

    subgraph DB["💾 Data Layer (SQLite)"]
        A["agents"]
        AP["agent_policies"]
        M["merchants"]
        P["products"]
        PUR["purchase_intents"]
        PI2["payment_intents"]
        T["transactions"]
        AE["audit_events"]
        R["receipts"]
    end

    subgraph EXT["🔗 External Systems"]
        RZ["Razorpay Test Mode"]
        EMB["SentenceTransformers<br/>all-MiniLM-L6-v2"]
        SK["scikit-learn TF-IDF<br/>(fallback)"]
    end

    %% User → AI
    USER -->|"types message" WEB
    WEB -->|"POST /api/v1/chat" CHAT

    %% AI → Gateway
    LLM -.->|"tool calls" MCP
    MCP -->|"HTTP REST" MCP_R
    LANG -->|"invoke" TXS

    %% Gateway → Domain
    CHAT --> INTENT
    CHAT --> PRODUCT
    CHAT --> NEG
    CHAT --> PAY
    PI --> TXS
    PM --> PMT
    TX --> SM
    TX --> TXS
    PR --> PRODUCT
    PL --> POL
    RC --> RCP
    MCP_R --> INTENT
    MCP_R --> PRODUCT
    MCP_R --> TXS
    MCP_R --> RCP

    %% Domain → Domain
    INTENT -->|"structured intent" PRODUCT
    PRODUCT -->|"ranked products" NEG
    NEG -->|"selected quote" PAY
    PAY -->|"purchase intent" TXS
    TXS --> POL
    POL -->|APPROVED| PMT
    POL -->|DENIED| SM
    PMT -->|reserve| PI2
    PMT -->|commit| RZR
    PMT -->|release| PI2
    RZR -->|payment result| PMT
    PMT -->|success| RCP
    RCP -->|receipt| SM
    PMT -->|failure| SM
    TXS -->|state transition| SM
    SM -->|audit event| AE

    %% Domain → DB
    A --> AP
    M --> P
    PUR --> T
    PI2 --> T
    T --> AE
    T --> R
    TXS -.-> PUR
    TXS -.-> PI2
    TXS -.-> T
    PMT -.-> PI2
    RCP -.-> R
    SM -.-> AE

    %% Domain → External
    PRODUCT -->|dense vectors| EMB
    PRODUCT -->|fallback| SK
    PMT -->|payment call| RZ

    %% Styling
    classDef layer fill:#1a1a2e,stroke:#16213e,stroke-width:2px,color:#e0e0e0
    classDef service fill:#0f3460,stroke:#1a5276,stroke-width:1px,color:#fff
    classDef data fill:#1b4332,stroke:#2d6a4f,stroke-width:1px,color:#fff
    classDef ext fill:#3d2c00,stroke:#8a7100,stroke-width:1px,color:#fff

    class UL,AI,DB,EXT layer
    class GW service
    class DOM,EMB,SK,RZ service
```

---

## 2. Transaction State Machine

```mermaid
stateDiagram-v2
    [*] --> CREATED: AI Buyer emits Purchase Intent
    CREATED --> POLICY_CHECKED: Policy evaluation starts

    POLICY_CHECKED --> APPROVED: All 4 rules pass
    POLICY_CHECKED --> DENIED: Any rule fails

    APPROVED --> PAYMENT_CREATED: Reserve funds (AUTHORIZED)
    DENIED --> [*]: TERMINAL — Zero funds touched

    PAYMENT_CREATED --> PAYMENT_SUCCESS: Razorpay captures
    PAYMENT_CREATED --> PAYMENT_FAILED: Card declined / error

    PAYMENT_FAILED --> [*]: TERMINAL — Hold released (RELEASED)

    PAYMENT_SUCCESS --> ORDER_CONFIRMED: Merchant order booked
    ORDER_CONFIRMED --> RECEIPT_GENERATED: Tax receipt issued
    RECEIPT_GENERATED --> [*]: FINAL SUCCESS — Funds committed (CAPTURED)

    state DENIED as "🔴 DENIED<br/>Terminal State<br/>No payment attempted"
    state PAYMENT_FAILED as "🟡 PAYMENT_FAILED<br/>Terminal State<br/>Hold released"
    state RECEIPT_GENERATED as "🟢 RECEIPT_GENERATED<br/>Final Success<br/>Funds committed"
```

### State Transition Rules

```mermaid
flowchart LR
    A["CREATED"] -->|only| B["POLICY_CHECKED"]
    B -->|APPROVED| C["APPROVED"]
    B -->|DENIED| D["DENIED ⛔ Terminal"]
    C -->|reserve| E["PAYMENT_CREATED"]
    E -->|success| F["PAYMENT_SUCCESS"]
    E -->|failure| G["PAYMENT_FAILED ⛔ Terminal"]
    F -->|order| H["ORDER_CONFIRMED"]
    H -->|receipt| I["RECEIPT_GENERATED ✅ Final"]
```

---

## 3. Two-Phase Reserve-Then-Commit Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant AI as AI Buyer Agent
    participant GW as AgentPay Gateway
    participant PE as Policy Engine
    participant DB as Database
    participant Pmt as Payment Service
    participant RZ as Razorpay Rails

    Note over U,RZ: PHASE 0: User Request
    U->>AI: "Auto-buy headphones under ₹5,000"
    AI->>GW: POST /api/v1/chat {message}

    Note over GW,DB: PHASE 1: Intent + Policy + Reserve
    GW->>GW: parse_intent_node → extract constraints
    GW->>DB: search_products (semantic + rules)
    GW->>DB: get_quote → selected product ₹4,499
    GW->>PE: evaluate_policy(agent_id, ₹4,499, audio, merchant_001)
    PE-->>GW: APPROVED ✓<br/>Per-tx: ₹5,000<br/>Daily: ₹20,000<br/>Category: allowed<br/>Merchant: allowed
    GW->>DB: CREATE PaymentIntent<br/>status=AUTHORIZED<br/>amount=₹4,499
    GW->>DB: AuditEvent(BUDGET_RESERVED)<br/>Available: ₹20,000 → ₹15,501
    GW->>DB: State=APPROVED→PAYMENT_CREATED
    GW-->>AI: Transaction AUTHORIZED<br/>Budget held

    Note over Pmt,RZ: PHASE 2A: Commit (Success)
    Pmt->>RZ: create_payment(₹4,499)
    RZ-->>Pmt: payment.captured (pay_xxx)
    Pmt->>DB: PaymentIntent.status=CAPTURED
    Pmt->>DB: AuditEvent(BUDGET_COMMITTED)
    Pmt->>DB: Order confirmed → stock decremented
    Pmt->>DB: Receipt generated (RCPT-20250905-XXXX)
    Pmt->>DB: State=ORDER_CONFIRMED→RECEIPT_GENERATED
    Pmt-->>AI: ✅ Order confirmed<br/>Receipt issued
    GW-->>U: Full receipt + audit trail

    Note over Pmt,RZ: PHASE 2B: Release (Failure)
    alt Payment Declined
        Pmt->>RZ: card_declined
        RZ-->>Pmt: PAYMENT_FAILED
        Pmt->>DB: PaymentIntent.status=RELEASED
        Pmt->>DB: AuditEvent(BUDGET_RELEASED)
        Pmt->>DB: Available budget restored ₹15,501→₹20,000
        Pmt->>DB: State=PAYMENT_FAILED (Terminal)
        Pmt-->>AI: ❌ Payment failed<br/>Budget fully restored<br/>Zero funds leaked
    end
```

---

## 4. Frontend Architecture

```mermaid
flowchart TB
    subgraph P["Pages"]
        HOME["index.tsx → /chat"]
        CHAT["chat.tsx"]
        CAT["catalog.tsx"]
        PL["policy.tsx"]
        TL["timeline.tsx"]
    end

    subgraph C["Shared Components"]
        NB["Navbar"]
        SB["Sidebar"]
        LC["InteractiveClarificationCard"]
        CCC["ConversationalCheckoutCard"]
        AET["AuditEventTrail"]
        RM["ReceiptModal"]
        SMC["StateMachineDiagram"]
        LG["Logo"]
    end

    subgraph L["API Layer"]
        API["lib/api.ts<br/>fetchProducts, sendChatMessage,<br/>fetchTransactions, updateAgentPolicy,<br/>reservePurchaseIntent, finalizeTransaction"]
    end

    subgraph S["State Types"]
        ST["ChatResponse<br/>Transaction<br/>CheckoutProposal<br/>AgentPolicy<br/>Clarification<br/>BudgetLifecycle"]
    end

    HOME --> CHAT
    HOME --> CAT
    HOME --> PL
    HOME --> TL
    CHAT --> LC
    CHAT --> CCC
    CHAT --> AET
    CHAT --> RM
    CHAT --> SMC
    PL --> API
    TL --> AET
    CAT --> API
    API --> L
    API --> S
```

---

## 5. MCP Server Architecture

```mermaid
flowchart TB
    subgraph CLIENTS["MCP Clients"]
        CLAUDE["Claude Desktop"]
        CURSOR["Cursor"]
        ANT["Antigravity"]
        CUSTOM["Any MCP Client"]
    end

    subgraph TRANSPORT["Transport Layer"]
        STDIO["stdio Transport<br/>(CLI)"]
        SSE["SSE / HTTP Transport<br/>(Remote Agents)"]
    end

    subgraph SERVER["AgentPay MCP Server"]
        MANIFEST["GET /manifest<br/>protocol_version: 2024-11-05"]
        TOOLS["GET /tools<br/>6 registered tools"]
        CALL["POST /tools/{name}/call<br/>Tool execution engine"]
        FORBIDDEN["🔒 Forbidden Tool Guard"]
    end

    subgraph SAFE_TOOLS["Safe Tool Registry"]
        T1["search_products<br/>Safe Discovery Rail"]
        T2["get_quote<br/>Safe Negotiation Rail"]
        T3["create_purchase_intent<br/>Policy-Supervised Intent Rail"]
        T4["get_transaction_status<br/>Read-Only Audit Rail"]
        T5["get_receipt<br/>Read-Only Audit Rail"]
        T6["request_clarification<br/>Human-in-the-Loop Rail"]
    end

    subgraph FORBIDDEN_TOOLS["🚫 Forbidden Tools"]
        F1["charge_card"]
        F2["transfer_money"]
        F3["modify_policy"]
        F4["modify_limits"]
        F5["access_payment_credentials"]
        F6["direct_debit"]
        F7["authorize_payment"]
    end

    CLIENTS --> TRANSPORT
    TRANSPORT --> SERVER
    SERVER --> FORBIDDEN
    FORBIDDEN -->|rejected 403| FORBIDDEN_TOOLS
    FORBIDDEN -->|allowed| SAFE_TOOLS
    SAFE_TOOLS --> DOMAIN["Domain Engine<br/>Policy + Payment + DB"]
```

---

## 6. Data Model Relationships

```mermaid
erDiagram
    agents ||--o{ agent_policies : "one-to-one"
    agents ||--o{ purchase_intents : "one-to-many"
    merchants ||--o{ products : "one-to-many"
    purchase_intents ||--o{ payment_intents : "one-to-one"
    purchase_intents ||--o{ transactions : "one-to-one"
    transactions ||--o{ audit_events : "one-to-many"
    transactions ||--o{ receipts : "one-to-one"
    payment_intents }|--|| transactions : "fk payment_intent_id"

    agents {
        string id PK
        string name
        string status
        datetime created_at
    }
    agent_policies {
        string id PK
        string agent_id FK
        float per_transaction_limit  default 5000.0
        float daily_spending_limit   default 20000.0
        json allowed_categories
        json blocked_merchants
        string currency              default "INR"
    }
    merchants {
        string id PK
        string name
        string status
        string currency
    }
    products {
        string id PK
        string merchant_id FK
        string name
        string brand
        string category
        float price
        int stock
        float rating
        json specs
    }
    purchase_intents {
        string id PK
        string agent_id FK
        string merchant_id FK
        string product_id FK
        float amount
        string status
        string idempotency_key
    }
    payment_intents {
        string id PK
        string purchase_intent_id FK UNIQUE
        string provider              default "RAZORPAY"
        string provider_payment_id
        float amount
        string status
        datetime reserved_at
        datetime committed_at
        datetime released_at
    }
    transactions {
        string id PK
        string purchase_intent_id FK UNIQUE
        string payment_intent_id FK
        string status
        datetime created_at
        datetime updated_at
    }
    audit_events {
        string id PK
        string transaction_id FK
        string event_type
        string actor_type
        json metadata_json
        datetime created_at
    }
    receipts {
        string id PK
        string transaction_id FK UNIQUE
        string receipt_number
        float amount
        string status
        json details
    }
```

---

## 7. Policy Engine Decision Flow

```mermaid
flowchart TD
    START["evaluate_policy<br/>(agent_id, amount, category, merchant_id)"] --> F1["Rule 1: Per-Transaction Limit<br/>amount ≤ per_transaction_limit?"]
    F1 -->|NO| REJECT1["DENIED<br/>TRANSACTION_LIMIT_EXCEEDED"]
    F1 -->|YES| F2["Rule 2: Rolling 24h Daily Limit<br/>spent_today + reserved + amount ≤ daily_limit?"]
    F2 -->|NO| REJECT2["DENIED<br/>DAILY_LIMIT_EXCEEDED"]
    F2 -->|YES| F3["Rule 3: Allowed Category<br/>category ∈ allowed_categories?"]
    F3 -->|NO| REJECT3["DENIED<br/>CATEGORY_NOT_ALLOWED"]
    F3 -->|YES| F4["Rule 4: Blocked Merchant<br/>merchant_id ∉ blocked_merchants?"]
    F4 -->|NO| REJECT4["DENIED<br/>MERCHANT_BLOCKED"]
    F4 -->|YES| APPROVE["APPROVED<br/>POLICY_APPROVED<br/>Available budget returned"]

    REJECT1 -->|terminal| STOP1["No PaymentIntent created<br/>No funds reserved<br/>AuditEvent: POLICY_EVALUATION_DENIED"]
    REJECT2 -->|terminal| STOP2["No PaymentIntent created<br/>No funds reserved"]
    REJECT3 -->|terminal| STOP3["No PaymentIntent created<br/>No funds reserved"]
    REJECT4 -->|terminal| STOP4["No PaymentIntent created<br/>No funds reserved"]
    APPROVE -->|proceed| RESERVE["Phase 1: Reserve<br/>PaymentIntent.status = AUTHORIZED<br/>Budget held"]

    classDef reject fill:#c0392b,stroke:#922b21,color:#fff
    classDef approve fill:#27ae60,stroke:#1e8449,color:#fff
    classDef check fill:#2980b9,stroke:#2471a3,color:#fff
    classDef terminal fill:#7f8c8d,stroke:#6c7a7a,color:#fff
    class REJECT1,REJECT2,REJECT3,REJECT4 reject
    class APPROVE approve
    class F1,F2,F3,F4 check
    class STOP1,STOP2,STOP3,STOP4 terminal
```

---

## 8. Project File Structure

```
AgentPay/
│
├── agentpay/                          # Core Domain Package
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py                  # SQLAlchemy ORM models (8 tables)
│   │   ├── seed.py                    # 135+ products, 3 merchants, 1 agent
│   │   └── __init__.py
│   ├── policy/
│   │   ├── __init__.py
│   │   └── engine.py                  # 4 deterministic rules + budget summary
│   ├── transactions/
│   │   ├── __init__.py
│   │   ├── state_machine.py           # 9-state deterministic FSM
│   │   └── service.py                 # 2-phase reserve-then-commit orchestration
│   ├── payments/
│   │   ├── __init__.py
│   │   ├── service.py                 # Reserve / Commit / Release
│   │   └── razorpay.py                # RazorpayAdapter + sandbox simulation
│   ├── merchants/
│   │   ├── __init__.py
│   │   ├── service.py                 # Search, quote, order confirm
│   │   └── retrieval.py               # Hybrid dense vector + TF-IDF search
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── buyer.py                   # AIBuyer: safe tool executor + chat
│   │   ├── graph.py                   # LangGraph 6-node pipeline
│   │   ├── intent.py                  # NLP constraint extraction
│   │   ├── product.py                 # Catalog discovery
│   │   ├── negotiator.py              # Quote comparison & selection
│   │   └── payment.py                 # Intent assembly & submission
│   ├── receipts/
│   │   ├── __init__.py
│   │   └── service.py                 # Receipt generation & retrieval
│   └── mcp/
│       ├── __init__.py
│       └── server.py                  # MCP Server: 6 safe tools + forbidden guard
│
├── apps/
│   ├── api/                           # FastAPI Backend :8000
│   │   ├── main.py                    # App factory, lifespan, CORS
│   │   ├── requirements.txt           # fastapi, sqlalchemy, razorpay, langgraph, etc.
│   │   └── routes/
│   │       ├── chat.py                # POST /api/v1/chat
│   │       ├── purchase_intents.py    # POST /api/v1/purchase-intents (+ /reserve)
│   │       ├── payments.py            # POST /api/v1/payment-intents
│   │       ├── transactions.py        # GET/POST /api/v1/transactions (+ /finalize)
│   │       ├── products.py            # GET /api/v1/products (+ /{id}/quote)
│   │       ├── policies.py            # GET/PUT /api/v1/agents/{id}/policy
│   │       ├── receipts.py            # GET /api/v1/receipts/{id}
│   │       ├── mcp.py                 # GET/POST /api/v1/mcp/*
│   │       └── webhooks.py            # POST /api/v1/payments/webhook
│   │
│   └── web/                           # Next.js Frontend :3000
│       ├── package.json
│       ├── next.config.js             # API rewrites to backend
│       ├── pages/
│       │   ├── _app.tsx               # Layout: Sidebar + Navbar
│       │   ├── index.tsx              # Redirect → /chat
│       │   ├── chat.tsx               # Main AI chat + checkout cards
│       │   ├── catalog.tsx            # Product browse + filters
│       │   ├── policy.tsx             # Budget dashboard + policy editor
│       │   └── timeline.tsx           # Transaction ledger + audit trail
│       ├── components/
│       │   ├── Sidebar.tsx
│       │   ├── Navbar.tsx
│       │   ├── Logo.tsx
│       │   ├── InteractiveClarificationCard.tsx
│       │   ├── ConversationalCheckoutCard.tsx
│       │   ├── AuditEventTrail.tsx
│       │   ├── ReceiptModal.tsx
│       │   ├── StateMachineDiagram.tsx
│       │   └── Navbar.tsx
│       ├── lib/
│       │   └── api.ts                 # TypeScript API client
│       ├── styles/
│       │   └── globals.css
│       └── tailwind.config.js
│
├── tests/                             # 34 Tests, All Passing
│   ├── conftest.py                    # In-memory SQLite fixture
│   ├── test_state_machine.py
│   ├── test_policy_engine.py
│   ├── test_purchase_intent_flow.py
│   ├── test_semantic_retrieval.py
│   ├── test_security_boundary.py
│   ├── test_multi_product_retrieval.py
│   ├── test_mcp_server.py
│   ├── test_langgraph_pipeline.py
│   └── run_tests.py
│
├── docs/
│   └── spec.md                        # Full product/technical spec
│
├── issues_fixed.md                    # Documented fixes applied
├── README.md
├── SYSTEM_DESIGN_AND_PROGRESS.md
├── SYSTEM_ARCHITECTURE.md             # This file
├── .env.example
└── agentpay.db                        # SQLite database
```

---

## 9. External Integrations

```mermaid
flowchart LR
    AGENTPAY["AgentPay System"]

    subgraph EXT1["Payment"]
        RZ_LIVE["Razorpay Live Mode<br/>rzp_test_* keys"]
        RZ_SANDBOX["Razorpay Sandbox<br/>(auto fallback if API fails)"]
    end

    subgraph EXT2["AI / LLM"]
        GEMINI["Gemini API"]
        OPENAI["OpenAI API"]
        FALLBACK["Rule-based Intent Parser<br/>(deterministic, no API needed)"]
    end

    subgraph EXT3["ML Models"]
        ST["SentenceTransformers<br/>all-MiniLM-L6-v2<br/>384-dim embeddings"]
        SKL["scikit-learn TF-IDF<br/>(fallback if ST unavailable)"]
    end

    subgraph EXT4["Protocol"]
        MCP_CLI["MCP Client<br/>(Claude Desktop, Cursor)"]
        HTTP_REST["HTTP REST Client<br/>(any API consumer)"]
    end

    AGENTPAY -->|payment order| RZ_LIVE
    AGENTPAY -->|sandbox sim| RZ_SANDBOX
    AGENTPAY -->|LLM key| GEMINI
    AGENTPAY -->|LLM key| OPENAI
    AGENTPAY -->|no key| FALLBACK
    AGENTPAY -->|embedder| ST
    AGENTPAY -->|fallback| SKL
    AGENTPAY -->|stdio| MCP_CLI
    AGENTPAY -->|HTTP| HTTP_REST
```

---

## 10. Deployment Architecture

```mermaid
flowchart TB
    subgraph LOCAL["Local Development"]
        FRONT["Next.js :3000"]
        BACK["FastAPI :8000"]
        DB["SQLite: agentpay.db"]
    end

    subgraph PROD["Production (Future)"]
        LB["Load Balancer"]
        API_G["FastAPI Instances"]
        WEB_G["Next.js Frontend"]
        PG["PostgreSQL"]
        REDIS["Redis Cache"]
        RZ_P["Razorpay Production"]
    end

    LOCAL --> FRONT
    LOCAL --> BACK
    LOCAL --> DB

    PROD --> LB
    LB --> API_G
    LB --> WEB_G
    API_G --> PG
    API_G --> REDIS
    API_G --> RZ_P
    WEB_G --> API_G
```

---

*Generated from `agentpay/` source code and `apps/` route definitions.*
*Verified against running tests: 34 passed, 0 warnings.*
