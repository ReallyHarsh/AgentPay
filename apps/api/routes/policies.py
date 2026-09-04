from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from agentpay.database.models import get_db, AgentPolicy, Agent
from agentpay.policy.engine import PolicyEngine

router = APIRouter(tags=["Policies"])


class PolicyEvaluateRequest(BaseModel):
    agent_id: str = Field(..., json_schema_extra={"example": "agent_001"})
    amount: float = Field(..., json_schema_extra={"example": 4499.0})
    category: str = Field(..., json_schema_extra={"example": "audio"})
    merchant_id: str = Field(..., json_schema_extra={"example": "merchant_001"})


class PolicyUpdateRequest(BaseModel):
    per_transaction_limit: Optional[float] = Field(None, json_schema_extra={"example": 10000.0})
    daily_spending_limit: Optional[float] = Field(None, json_schema_extra={"example": 25000.0})
    allowed_categories: Optional[List[str]] = Field(None, json_schema_extra={"example": ["electronics", "audio", "accessories", "books"]})
    blocked_merchants: Optional[List[str]] = Field(None, json_schema_extra={"example": []})


@router.post("/policies/evaluate")
def evaluate_policy(
    payload: PolicyEvaluateRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluates spending limit, category check, and merchant blocklist.
    Called internally by purchase intent handler or testing tools.
    """
    result = PolicyEngine.evaluate(
        agent_id=payload.agent_id,
        amount=payload.amount,
        category=payload.category,
        merchant_id=payload.merchant_id,
        db=db
    )
    return result.to_dict()


@router.get("/agents/{agent_id}/policy")
def get_agent_policy(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    Get policy settings for an agent including rolling 24h spent amount,
    active reservations, and remaining available budget.
    """
    policy = db.query(AgentPolicy).filter(AgentPolicy.agent_id == agent_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found for agent")

    budget = PolicyEngine.get_budget_summary(agent_id, db)

    return {
        "id": policy.id,
        "agent_id": policy.agent_id,
        "currency": policy.currency,
        "per_transaction_limit": policy.per_transaction_limit,
        "daily_spending_limit": getattr(policy, "daily_spending_limit", 20000.0) or 20000.0,
        "spent_today": budget["spent_today"],
        "currently_reserved": budget["currently_reserved"],
        "available_budget": budget["available_budget"],
        "allowed_categories": policy.allowed_categories,
        "blocked_merchants": policy.blocked_merchants,
        "created_at": policy.created_at.isoformat() if policy.created_at else None
    }


@router.put("/agents/{agent_id}/policy")
def update_agent_policy(
    agent_id: str,
    payload: PolicyUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update spending limits, allowed categories, and blocked merchants.
    """
    policy = db.query(AgentPolicy).filter(AgentPolicy.agent_id == agent_id).first()
    if not policy:
        policy = AgentPolicy(
            id=f"policy_{agent_id}",
            agent_id=agent_id,
            currency="INR",
            per_transaction_limit=payload.per_transaction_limit or 5000.0,
            daily_spending_limit=payload.daily_spending_limit or 20000.0
        )
        db.add(policy)

    if payload.per_transaction_limit is not None:
        policy.per_transaction_limit = payload.per_transaction_limit

    if payload.daily_spending_limit is not None:
        policy.daily_spending_limit = payload.daily_spending_limit

    if payload.allowed_categories is not None:
        policy.allowed_categories = payload.allowed_categories

    if payload.blocked_merchants is not None:
        policy.blocked_merchants = payload.blocked_merchants

    db.commit()
    db.refresh(policy)

    budget = PolicyEngine.get_budget_summary(agent_id, db)

    return {
        "message": "Policy updated successfully",
        "policy": {
            "id": policy.id,
            "agent_id": policy.agent_id,
            "currency": policy.currency,
            "per_transaction_limit": policy.per_transaction_limit,
            "daily_spending_limit": policy.daily_spending_limit,
            "spent_today": budget["spent_today"],
            "currently_reserved": budget["currently_reserved"],
            "available_budget": budget["available_budget"],
            "allowed_categories": policy.allowed_categories,
            "blocked_merchants": policy.blocked_merchants
        }
    }
