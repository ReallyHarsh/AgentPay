import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from agentpay.database.models import Base
from agentpay.database.seed import seed_database
from agentpay.merchants.service import MerchantService
from agentpay.agents.buyer import AIBuyer
from agentpay.agents.intent import IntentAgent


@pytest.fixture(scope="module")
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    seed_database(db)
    yield db
    db.close()


def test_earbuds_vs_headphones_discrimination(test_db):
    """
    Test that searching for 'wireless earbuds under 5000' prioritizes actual earbuds
    (realme Buds Air 5 Pro or boAt Airdopes 141) and does NOT rank over-ear headphones (JBL 770NC) ahead of them.
    """
    results = MerchantService.search_products(
        query="wireless earbuds under 5000",
        db=test_db
    )
    assert len(results) > 0
    top = results[0]
    assert top["price"] <= 5000.0
    # Must be earbuds, not over-ear headphones
    assert top["sub_type"] == "earbuds"
    assert "earbud" in top["name"].lower() or "airdopes" in top["name"].lower()
    # Conflicting over-ear headphones must not be #1
    assert "over-ear" not in top["name"].lower()


def test_over_ear_headphones_discrimination(test_db):
    """
    Test that searching for 'over-ear ANC headphones under 5000' returns over-ear headphones (JBL 770NC),
    not in-ear earbuds.
    """
    results = MerchantService.search_products(
        query="over-ear ANC headphones under 5000",
        db=test_db
    )
    assert len(results) > 0
    top = results[0]
    assert top["price"] <= 5000.0
    assert top["sub_type"] == "headphones"
    assert "770nc" in top["id"].lower() or "over-ear" in top["name"].lower()


def test_mouse_query_excludes_webcam_and_keyboard(test_db):
    """
    Test that searching for 'Logitech mouse' ranks mice (Lift / MX Master) at the top,
    and never ranks Logitech webcams (Brio) or keyboards above mice.
    """
    results = MerchantService.search_products(
        query="Logitech mouse",
        db=test_db
    )
    assert len(results) >= 2
    top_2 = results[:2]
    for r in top_2:
        assert r["sub_type"] == "mouse"
        assert "mouse" in r["name"].lower() or "lift" in r["name"].lower()


def test_tiered_options_form_factor_consistency(test_db):
    """
    Test that AIBuyer tiered options (Budget Friendly vs Premium Flagship)
    maintain the exact same form factor as the requested product (e.g. mice only for mouse query).
    """
    buyer = AIBuyer("agent_001")
    res = buyer.chat("Logitech mouse", db=test_db)
    proposal = res.get("proposal")
    assert proposal is not None
    assert "mouse" in proposal["name"].lower() or "lift" in proposal["name"].lower()

    tiered = proposal.get("tiered_options", [])
    assert len(tiered) >= 2
    for opt in tiered:
        assert "webcam" not in opt["name"].lower()
        assert "keyboard" not in opt["name"].lower()


def test_new_category_smartwatch_retrieval(test_db):
    """
    Test that searching for smartwatches in the newly seeded category
    accurately discovers smartwatches by spec (AMOLED), budget, and brand.
    """
    # 1. Budget AMOLED smartwatch
    results = MerchantService.search_products(
        query="smartwatch with AMOLED under 5000",
        db=test_db
    )
    assert len(results) > 0
    top = results[0]
    assert top["category"] == "wearables"
    assert top["price"] <= 5000.0
    assert "noise" in top["brand"].lower() or "colorfit" in top["id"].lower()

    # 2. Apple Watch exact discovery
    apple_results = MerchantService.search_products(
        query="Apple Watch Series 9",
        db=test_db
    )
    assert len(apple_results) > 0
    assert "apple watch" in apple_results[0]["name"].lower()

    # 3. Long battery life smartwatch
    battery_results = MerchantService.search_products(
        query="smartwatch with 100 hours battery",
        db=test_db
    )
    assert len(battery_results) > 0
    assert "oneplus watch 2" in battery_results[0]["name"].lower()


def test_model_number_preservation_in_intent(test_db):
    """
    Test that IntentAgent preserves alphanumeric model codes (770NC, 550, K2, XPS 15, Series 9).
    """
    parsed1 = IntentAgent.parse_intent("Buy JBL 770NC headphones under 5000")
    assert "770nc" in parsed1["clean_query"]
    assert parsed1["max_price"] == 5000.0

    parsed2 = IntentAgent.parse_intent("Find Dell XPS 15 OLED laptop")
    assert "15" in parsed2["clean_query"]
    assert "xps" in parsed2["clean_query"]

    parsed3 = IntentAgent.parse_intent("Show Apple Watch Series 9")
    assert "9" in parsed3["clean_query"]
    assert parsed3["sub_type"] == "smartwatch"
    assert parsed3["category"] == "wearables"
