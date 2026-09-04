import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from agentpay.database.models import Base
from agentpay.database.seed import seed_database
from agentpay.merchants.service import MerchantService
from agentpay.agents.buyer import AIBuyer


@pytest.fixture(scope="module")
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    seed_database(db)
    yield db
    db.close()


def test_headphones_under_budget_constraint(test_db):
    """
    Test that 'wireless headphones with ANC under 5000' correctly returns
    JBL 770NC (under ₹5,000) and filters/penalizes ₹35,900 Bose and ₹25,490 Sony.
    """
    results = MerchantService.search_products(
        query="wireless headphones with ANC under 5000",
        db=test_db
    )
    assert len(results) > 0
    top = results[0]
    assert top["price"] <= 5000.0, f"Expected top result under 5000, got {top['name']} at Rs.{top['price']}"
    assert "770nc" in top["id"].lower() or "jbl" in top["brand"].lower()


def test_ergonomic_mouse_relevance(test_db):
    """
    Test that 'ergonomic mouse for programming' returns mice (Logitech Lift / MX Master),
    NEVER a Mini PC or irrelevant computer hardware.
    """
    results = MerchantService.search_products(
        query="ergonomic mouse for programming",
        db=test_db
    )
    assert len(results) > 0
    top_3 = results[:3]
    for r in top_3:
        assert r["category"] in ("accessories", "office"), f"Unexpected category {r['category']} for mouse search"
        assert "mouse" in r["name"].lower() or "lift" in r["name"].lower() or "mx master" in r["name"].lower()


def test_4k_monitor_coding_relevance(test_db):
    """
    Test that '4k monitor for coding' returns 4K displays (BenQ, Dell, LG).
    """
    results = MerchantService.search_products(
        query="4k monitor for coding",
        db=test_db
    )
    assert len(results) > 0
    top_3 = results[:3]
    for r in top_3:
        assert r["category"] == "displays"
        assert "4k" in r["name"].lower() or "4k" in (r.get("description") or "").lower()


def test_mechanical_keyboard_relevance(test_db):
    """
    Test that 'mechanical keyboard' returns Keychron mechanical keyboards.
    """
    results = MerchantService.search_products(
        query="mechanical keyboard",
        db=test_db
    )
    assert len(results) > 0
    top = results[0]
    assert "keyboard" in top["name"].lower()
    assert "keychron" in top["brand"].lower()


def test_quote_comparison_cheapest_mode(test_db):
    """
    Test that AIBuyer with 'cheapest' preference selects the lowest price quote.
    """
    buyer = AIBuyer("agent_001")
    result = buyer.run("buy cheapest wireless ANC headphones under 5000", db=test_db)
    assert result is not None
    proposal = result.get("proposal")
    assert proposal is not None
    # boAt Rockerz 550 or JBL Tune 770NC Reliance (cheaper than standard Croma)
    assert proposal["price"] <= 4499.0
    assert "lowest guaranteed price" in proposal.get("rationale", "").lower()
