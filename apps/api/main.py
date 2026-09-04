import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure root package agentpay is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from agentpay.database.models import init_db
from agentpay.database.seed import seed_database
from apps.api.routes import (
    purchase_intents,
    policies,
    payments,
    transactions,
    products,
    receipts,
    chat,
    webhooks,
    mcp,
    protocol
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and seed data
    init_db()
    seed_database()
    print("[AgentPay API] Database initialized & seeded successfully.")
    
    # Pre-warm semantic search embeddings to avoid cold-start lag on first user query
    try:
        from agentpay.merchants.retrieval import get_embedder
        get_embedder()
        print("[AgentPay API] Embedding model pre-warmed successfully.")
    except Exception as e:
        print(f"[AgentPay API] Model pre-warm note: {e}")
        
    yield


app = FastAPI(
    title="AgentPay API",
    description="Trust and Payment-Control Layer for Autonomous AI Commerce",
    version="1.1.0",
    lifespan=lifespan
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(protocol.router) # Root level /.well-known/*, /llms.txt, and /api/v1/protocol/*
app.include_router(products.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1")
app.include_router(purchase_intents.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(receipts.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(mcp.router, prefix="/api/v1")


@app.get("/", tags=["Root"])
def root():
    return {
        "service": "AgentPay API",
        "status": "ONLINE",
        "version": "1.1.0",
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
        "description": "Trust and Payment-Control Layer for Autonomous AI Commerce"
    }


@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": "AgentPay API",
        "version": "1.0.0",
        "core_rule": "AI can decide, only AgentPay can authorize money."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
