from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from agentpay.database.models import get_db
from agentpay.agents.buyer import AIBuyer

router = APIRouter(prefix="/chat", tags=["AI Buyer Chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., json_schema_extra={"example": "Buy headphones under ₹5,000"})
    agent_id: str = Field("agent_001", json_schema_extra={"example": "agent_001"})


@router.post("")
def chat_with_buyer(
    payload: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Send prompt to Single Autonomous AI Buyer Agent. Operates via an iterative multi-tool calling
    loop (search_products -> get_quote -> create_purchase_intent -> get_receipt), supports human-in-the-loop
    clarifying questions (HITL v1.2), and returns interactive in-app checkout proposals.
    """
    buyer = AIBuyer(agent_id=payload.agent_id)
    result = buyer.chat(user_message=payload.message, db=db)
    return result
