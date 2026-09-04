from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from agentpay.database.models import AgentPolicy, Agent, PurchaseIntent, Transaction, TransactionStatus


@dataclass
class PolicyEvaluationResult:
    approved: bool
    code: str
    reason: str
    limit: float
    requested_amount: float
    currency: str = "INR"
    daily_limit: Optional[float] = None
    spent_today: Optional[float] = None
    currently_reserved: Optional[float] = 0.0
    available_budget: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "code": self.code,
            "reason": self.reason,
            "limit": self.limit,
            "requested_amount": self.requested_amount,
            "currency": self.currency,
            "daily_limit": self.daily_limit,
            "spent_today": self.spent_today,
            "currently_reserved": self.currently_reserved,
            "available_budget": self.available_budget
        }


class PolicyEngine:
    """
    Deterministic Policy Engine for AgentPay.
    Evaluates spending limits (per-transaction and rolling 24h daily limit),
    in-flight active reservations, allowed categories, and merchant blocklists.
    """

    @staticmethod
    def calculate_rolling_24h_spend(agent_id: str, db: Session) -> float:
        """
        Calculates cumulative committed spend by agent in the last 24 hours
        for transactions that successfully captured payment.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        successful_statuses = [
            TransactionStatus.PAYMENT_SUCCESS.value,
            TransactionStatus.ORDER_CONFIRMED.value,
            TransactionStatus.RECEIPT_GENERATED.value
        ]

        query = (
            db.query(PurchaseIntent.amount)
            .join(Transaction, Transaction.purchase_intent_id == PurchaseIntent.id)
            .filter(
                PurchaseIntent.agent_id == agent_id,
                Transaction.status.in_(successful_statuses),
                Transaction.created_at >= cutoff
            )
        )
        amounts = [row[0] for row in query.all()]
        return float(sum(amounts))

    @staticmethod
    def calculate_active_reservations(agent_id: str, db: Session) -> float:
        """
        Calculates in-flight reserved amounts held against agent's daily limit
        that are awaiting payment capture or release.
        """
        from agentpay.database.models import PaymentIntent
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)

        query = (
            db.query(PurchaseIntent.amount)
            .join(PaymentIntent, PaymentIntent.purchase_intent_id == PurchaseIntent.id)
            .filter(
                PurchaseIntent.agent_id == agent_id,
                PaymentIntent.status.in_(["AUTHORIZED", "RESERVED"]),
                PaymentIntent.created_at >= cutoff
            )
        )
        amounts = [row[0] for row in query.all()]
        return float(sum(amounts))

    @staticmethod
    def get_budget_summary(agent_id: str, db: Session) -> dict:
        """
        Returns full breakdown of agent spending limits, committed 24h spend,
        in-flight reservations, and currently available unreserved budget.
        """
        policy = db.query(AgentPolicy).filter(AgentPolicy.agent_id == agent_id).first()
        per_tx_limit = policy.per_transaction_limit if policy else 5000.0
        daily_limit = getattr(policy, "daily_spending_limit", 20000.0) or 20000.0
        currency = policy.currency if policy else "INR"
        spent_today = PolicyEngine.calculate_rolling_24h_spend(agent_id, db)
        currently_reserved = PolicyEngine.calculate_active_reservations(agent_id, db)
        available_budget = max(0.0, daily_limit - (spent_today + currently_reserved))

        return {
            "per_transaction_limit": per_tx_limit,
            "daily_spending_limit": daily_limit,
            "spent_today": spent_today,
            "currently_reserved": currently_reserved,
            "available_budget": available_budget,
            "currency": currency
        }

    @staticmethod
    def evaluate(
        agent_id: str,
        amount: float,
        category: str,
        merchant_id: str,
        db: Session
    ) -> PolicyEvaluationResult:
        # Fetch policy for agent
        policy = db.query(AgentPolicy).filter(AgentPolicy.agent_id == agent_id).first()

        if not policy:
            # Fallback default policy if none found in DB
            limit = 5000.0
            daily_limit = 20000.0
            allowed_categories = ["electronics", "audio", "accessories", "books", "office"]
            blocked_merchants = []
            currency = "INR"
        else:
            limit = policy.per_transaction_limit
            daily_limit = getattr(policy, "daily_spending_limit", 20000.0) or 20000.0
            allowed_categories = policy.allowed_categories
            blocked_merchants = policy.blocked_merchants
            currency = policy.currency

        spent_today = PolicyEngine.calculate_rolling_24h_spend(agent_id, db)
        currently_reserved = PolicyEngine.calculate_active_reservations(agent_id, db)
        available_budget = max(0.0, daily_limit - (spent_today + currently_reserved))

        # Rule 1: Per-transaction spending limit check
        if amount > limit:
            return PolicyEvaluationResult(
                approved=False,
                code="TRANSACTION_LIMIT_EXCEEDED",
                reason=f"Requested amount ₹{amount:,.2f} exceeds agent per-transaction limit of ₹{limit:,.2f}.",
                limit=limit,
                requested_amount=amount,
                currency=currency,
                daily_limit=daily_limit,
                spent_today=spent_today,
                currently_reserved=currently_reserved,
                available_budget=available_budget
            )

        # Rule 2: Rolling 24-Hour Daily Spending Limit Check (inclusive of active reserves)
        if daily_limit and (spent_today + currently_reserved + amount) > daily_limit:
            return PolicyEvaluationResult(
                approved=False,
                code="DAILY_LIMIT_EXCEEDED",
                reason=f"Requested amount ₹{amount:,.2f} plus active reservations (₹{currently_reserved:,.2f}) and 24h spend (₹{spent_today:,.2f}) exceeds daily limit of ₹{daily_limit:,.2f}.",
                limit=daily_limit,
                requested_amount=amount,
                currency=currency,
                daily_limit=daily_limit,
                spent_today=spent_today,
                currently_reserved=currently_reserved,
                available_budget=available_budget
            )

        # Rule 3: Allowed product category check
        if allowed_categories:
            norm_allowed = [c.lower().strip() for c in allowed_categories]
            if category.lower().strip() not in norm_allowed:
                return PolicyEvaluationResult(
                    approved=False,
                    code="CATEGORY_NOT_ALLOWED",
                    reason=f"Product category '{category}' is not in allowed categories ({', '.join(allowed_categories)}).",
                    limit=limit,
                    requested_amount=amount,
                    currency=currency,
                    daily_limit=daily_limit,
                    spent_today=spent_today,
                    currently_reserved=currently_reserved,
                    available_budget=available_budget
                )

        # Rule 4: Blocked merchant check
        if blocked_merchants and merchant_id in blocked_merchants:
            return PolicyEvaluationResult(
                approved=False,
                code="MERCHANT_BLOCKED",
                reason=f"Merchant '{merchant_id}' is currently blocked by agent policy.",
                limit=limit,
                requested_amount=amount,
                currency=currency,
                daily_limit=daily_limit,
                spent_today=spent_today,
                currently_reserved=currently_reserved,
                available_budget=available_budget
            )

        # All checks passed
        return PolicyEvaluationResult(
            approved=True,
            code="POLICY_APPROVED",
            reason=f"Transaction of ₹{amount:,.2f} complies with all policy rules (Per-tx: ₹{limit:,.2f}, Daily: ₹{daily_limit:,.2f}, Available: ₹{available_budget:,.2f}).",
            limit=limit,
            requested_amount=amount,
            currency=currency,
            daily_limit=daily_limit,
            spent_today=spent_today,
            currently_reserved=currently_reserved,
            available_budget=available_budget
        )
