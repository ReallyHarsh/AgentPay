import os
import json
from datetime import datetime, timezone
from typing import Generator
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    Enum as SQLEnum
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
import enum

Base = declarative_base()

try:
    from dotenv import load_dotenv
    # Load .env from project root
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
except ImportError:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "agentpay.db").replace("\\", "/")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
# Normalize postgres:// to postgresql:// for SQLAlchemy compatibility with Supabase/Render
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TransactionStatus(str, enum.Enum):
    CREATED = "CREATED"
    POLICY_CHECKED = "POLICY_CHECKED"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    PAYMENT_CREATED = "PAYMENT_CREATED"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    RECEIPT_GENERATED = "RECEIPT_GENERATED"


class ActorType(str, enum.Enum):
    USER = "USER"
    AI_BUYER = "AI_BUYER"
    POLICY_ENGINE = "POLICY_ENGINE"
    PAYMENT_SERVICE = "PAYMENT_SERVICE"
    MERCHANT_SERVICE = "MERCHANT_SERVICE"
    SYSTEM = "SYSTEM"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    status = Column(String(32), default="ACTIVE")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    policy = relationship("AgentPolicy", back_populates="agent", uselist=False)
    purchase_intents = relationship("PurchaseIntent", back_populates="agent")


class AgentPolicy(Base):
    __tablename__ = "agent_policies"

    id = Column(String(64), primary_key=True)
    agent_id = Column(String(64), ForeignKey("agents.id"), unique=True, nullable=False)
    currency = Column(String(8), default="INR")
    per_transaction_limit = Column(Float, default=5000.0)
    daily_spending_limit = Column(Float, default=20000.0)
    _allowed_categories = Column("allowed_categories", Text, default="[\"electronics\", \"audio\", \"accessories\", \"books\", \"office\"]")
    _blocked_merchants = Column("blocked_merchants", Text, default="[]")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    agent = relationship("Agent", back_populates="policy")

    @property
    def allowed_categories(self) -> list:
        try:
            return json.loads(self._allowed_categories) if self._allowed_categories else []
        except Exception:
            return []

    @allowed_categories.setter
    def allowed_categories(self, value: list):
        self._allowed_categories = json.dumps(value)

    @property
    def blocked_merchants(self) -> list:
        try:
            return json.loads(self._blocked_merchants) if self._blocked_merchants else []
        except Exception:
            return []

    @blocked_merchants.setter
    def blocked_merchants(self, value: list):
        self._blocked_merchants = json.dumps(value)


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    status = Column(String(32), default="ACTIVE")
    currency = Column(String(8), default="INR")

    products = relationship("Product", back_populates="merchant")


class Product(Base):
    __tablename__ = "products"

    id = Column(String(64), primary_key=True)
    merchant_id = Column(String(64), ForeignKey("merchants.id"), nullable=False)
    name = Column(String(256), nullable=False)
    brand = Column(String(64), nullable=True, default="")
    description = Column(Text, default="")
    category = Column(String(64), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    stock = Column(Integer, default=100)
    rating = Column(Float, default=4.8)
    _specs = Column("specs", Text, default="{}")

    merchant = relationship("Merchant", back_populates="products")

    @property
    def specs(self) -> dict:
        try:
            return json.loads(self._specs) if self._specs else {}
        except Exception:
            return {}

    @specs.setter
    def specs(self, value: dict):
        self._specs = json.dumps(value)


class PurchaseIntent(Base):
    __tablename__ = "purchase_intents"

    id = Column(String(64), primary_key=True)
    agent_id = Column(String(64), ForeignKey("agents.id"), nullable=False)
    merchant_id = Column(String(64), ForeignKey("merchants.id"), nullable=False)
    product_id = Column(String(64), ForeignKey("products.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    status = Column(String(32), default="CREATED")
    idempotency_key = Column(String(128), unique=True, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    agent = relationship("Agent", back_populates="purchase_intents")
    merchant = relationship("Merchant")
    product = relationship("Product")
    payment_intent = relationship("PaymentIntent", back_populates="purchase_intent", uselist=False)
    transaction = relationship("Transaction", back_populates="purchase_intent", uselist=False)


class PaymentIntentStatus(str, enum.Enum):
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"   # Razorpay literal: funds authorized & held against budget
    CAPTURED = "CAPTURED"       # Razorpay literal: funds captured & permanently committed
    RELEASED = "RELEASED"       # Authorization hold voided & released back to available budget
    FAILED = "FAILED"           # Payment failed / declined by issuer
    RESERVED = "AUTHORIZED"     # Alias for backwards compatibility
    COMMITTED = "CAPTURED"      # Alias for backwards compatibility


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id = Column(String(64), primary_key=True)
    purchase_intent_id = Column(String(64), ForeignKey("purchase_intents.id"), unique=True, nullable=False)
    provider = Column(String(32), default="RAZORPAY")
    provider_payment_id = Column(String(128), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    status = Column(String(32), default="CREATED")
    reserved_at = Column(DateTime, nullable=True)
    committed_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    purchase_intent = relationship("PurchaseIntent", back_populates="payment_intent")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(64), primary_key=True)
    purchase_intent_id = Column(String(64), ForeignKey("purchase_intents.id"), unique=True, nullable=False)
    payment_intent_id = Column(String(64), ForeignKey("payment_intents.id"), nullable=True)
    status = Column(String(32), default=TransactionStatus.CREATED.value)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    purchase_intent = relationship("PurchaseIntent", back_populates="transaction")
    audit_events = relationship("AuditEvent", back_populates="transaction", order_by="AuditEvent.created_at")
    receipt = relationship("Receipt", back_populates="transaction", uselist=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(64), primary_key=True)
    transaction_id = Column(String(64), ForeignKey("transactions.id"), nullable=False)
    event_type = Column(String(64), nullable=False)
    actor_type = Column(String(32), nullable=False)
    metadata_json = Column("metadata_json", Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    transaction = relationship("Transaction", back_populates="audit_events")

    @property
    def event_metadata(self) -> dict:
        try:
            return json.loads(self.metadata_json) if self.metadata_json else {}
        except Exception:
            return {}

    @event_metadata.setter
    def event_metadata(self, value: dict):
        self.metadata_json = json.dumps(value)


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(String(64), primary_key=True)
    transaction_id = Column(String(64), ForeignKey("transactions.id"), unique=True, nullable=False)
    receipt_number = Column(String(64), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    status = Column(String(32), default="ISSUED")
    _details = Column("details", Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    transaction = relationship("Transaction", back_populates="receipt")

    @property
    def details(self) -> dict:
        try:
            return json.loads(self._details) if self._details else {}
        except Exception:
            return {}

    @details.setter
    def details(self, value: dict):
        self._details = json.dumps(value)


def init_db():
    from sqlalchemy import text
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        for col in ["reserved_at", "committed_at", "released_at"]:
            try:
                conn.execute(text(f"ALTER TABLE payment_intents ADD COLUMN {col} DATETIME"))
                conn.commit()
            except Exception:
                pass
