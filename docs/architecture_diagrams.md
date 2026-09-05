# AgentPay Architecture Diagrams (Excalidraw Compatible)

You can easily import these into Excalidraw by going to **Insert > Mermaid**, pasting the code, and clicking **Insert**.

## 1. High-Level System Architecture

This diagram shows the complete topology of AgentPay from the User/AI Layer all the way down to the Razorpay Settlement Rails.

```mermaid
flowchart TD
    subgraph ClientLayer ["1. Client & External Ecosystem"]
        User["User / Enterprise Admin"]
        AIBuyer["Autonomous AI Buyer (LangGraph)"]
        BrowserUI["Modern Paper Web UI (Next.js)"]
    end

    subgraph ProtocolLayer ["2. Standardized Protocol Ingress"]
        ACP["/.well-known/agent-catalog.json"]
        UAP["/.well-known/uap-manifest.json"]
        X402["/api/v1/protocol/x402/checkout"]
        MCP["Model Context Protocol (MCP)"]
    end

    subgraph GatewayCore ["3. AgentPay Gateway Core"]
        API["FastAPI Routing Engine"]
        
        subgraph AgentSquad ["AI Agent Squad"]
            IntentAg["Intent Agent"]
            ProductAg["Product Agent"]
            NegoAg["Negotiation Agent"]
            PayAg["Payment Agent"]
        end
        
        PolicyEngine["Deterministic Policy Engine"]
        StateMachine["7-Stage State Machine"]
        AuditLogger["Immutable Audit Subsystem"]
    end

    subgraph SettlementLayer ["4. Financial Settlement Layer"]
        PaymentService["Two-Phase Reserve-Commit Service"]
        RazorpayAdapter["Razorpay Test Adapter"]
        RZP["Razorpay Test API Rails"]
        Webhooks["HMAC-SHA256 Webhook Receiver"]
    end

    subgraph PersistenceLayer ["5. Data Persistence"]
        DB[(SQLite / PostgreSQL Ledger)]
    end

    User --> BrowserUI
    BrowserUI --> API
    AIBuyer --> ProtocolLayer
    ProtocolLayer --> API
    API --> AgentSquad
    AgentSquad --> PolicyEngine
    PolicyEngine --> StateMachine
    StateMachine --> PaymentService
    PaymentService --> RazorpayAdapter
    RazorpayAdapter --> RZP
    RZP -.->|Async Event| Webhooks
    Webhooks --> StateMachine
    StateMachine --> AuditLogger
    AuditLogger --> DB
    PolicyEngine --> DB
```

---

## 2. Two-Phase Reserve-Then-Commit Lifecycle

This diagram illustrates how AgentPay secures the budget before making any calls to the Razorpay API, ensuring no financial leaks occur.

```mermaid
stateDiagram-v2
    [*] --> PolicyApproved: Policy Evaluated OK
    PolicyApproved --> Phase1_Authorized: Phase 1 (Reserve)
    note right of Phase1_Authorized
        PaymentIntent: AUTHORIZED
        Amount immediately locked from agent available budget.
        Audit Event: BUDGET_RESERVED
    end note

    Phase1_Authorized --> RazorpayExecution: Call Razorpay Rails
    
    RazorpayExecution --> Phase2A_Captured: Payment Succeeded
    note right of Phase2A_Captured
        PaymentIntent: CAPTURED
        Amount permanently committed.
        Order confirmed with merchant.
        Audit Event: BUDGET_COMMITTED
    end note
    
    RazorpayExecution --> Phase2B_Released: Payment Declined / Error
    note right of Phase2B_Released
        PaymentIntent: RELEASED
        Reservation voided.
        Amount restored to available budget.
        Audit Event: BUDGET_RELEASED
    end note

    Phase2A_Captured --> [*]
    Phase2B_Released --> [*]
```

---

## 3. Transaction State Machine

This shows the deterministic 7 stages of a transaction, highlighting the terminal `DENIED` state which guarantees zero unauthorized charges.

```mermaid
stateDiagram-v2
    [*] --> CREATED: AI Buyer Squad emits Purchase Intent
    CREATED --> POLICY_CHECKED: Evaluate spending limits, velocity & categories

    POLICY_CHECKED --> APPROVED: Policy constraints satisfied
    POLICY_CHECKED --> DENIED: Limit exceeded / category blocked / merchant invalid

    APPROVED --> PAYMENT_CREATED: Payment intent initiated with Razorpay
    DENIED --> [*]: TERMINAL STATE (Zero financial contact)

    PAYMENT_CREATED --> PAYMENT_SUCCESS: Razorpay authorization & capture success
    PAYMENT_CREATED --> PAYMENT_FAILED: Provider error / card declined

    PAYMENT_FAILED --> [*]: TERMINAL STATE

    PAYMENT_SUCCESS --> ORDER_CONFIRMED: Merchant stock reserved & order booked
    ORDER_CONFIRMED --> RECEIPT_GENERATED: Final itemized tax receipt issued
    RECEIPT_GENERATED --> [*]: FINAL SUCCESS
```
