"""
API endpoint tests.

Uses FastAPI's TestClient with SQLite in-memory via dependency override.
No running server or PostgreSQL required.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from db.schema import Base
from api.deps import get_engine
from main import app

REAL_HANDS = Path(__file__).parent / "fixtures" / "hand_histories" / "real_hands"
SAMPLE_FILE = REAL_HANDS / "GG20231205-1004 - RushAndCash15083753 - 0.02 - 0.05 - 6max.txt"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def client(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def populated_client(client):
    """Client with SAMPLE_FILE already imported."""
    with open(SAMPLE_FILE, "rb") as f:
        client.post("/import", files=[("files", ("sample.txt", f, "text/plain"))])
    return client


# ---------------------------------------------------------------------------
# POST /import
# ---------------------------------------------------------------------------

class TestImportEndpoint:
    def test_returns_200(self, client):
        with open(SAMPLE_FILE, "rb") as f:
            resp = client.post("/import", files=[("files", ("sample.txt", f, "text/plain"))])
        assert resp.status_code == 200

    def test_returns_imported_count_matching_parser(self, client):
        from parsers.ggpoker import GGPokerParser
        expected = len(GGPokerParser().parse_file(SAMPLE_FILE))
        with open(SAMPLE_FILE, "rb") as f:
            resp = client.post("/import", files=[("files", ("sample.txt", f, "text/plain"))])
        data = resp.json()
        assert data["imported"] == expected
        assert data["skipped"] == 0
        assert data["errors"] == []

    def test_reimport_skips_all(self, client):
        for _ in range(2):
            with open(SAMPLE_FILE, "rb") as f:
                resp = client.post("/import", files=[("files", ("sample.txt", f, "text/plain"))])
        data = resp.json()
        assert data["imported"] == 0
        assert data["skipped"] > 0

    def test_reimport_skipped_count_matches_parser(self, client):
        from parsers.ggpoker import GGPokerParser
        expected = len(GGPokerParser().parse_file(SAMPLE_FILE))
        for _ in range(2):
            with open(SAMPLE_FILE, "rb") as f:
                resp = client.post("/import", files=[("files", ("sample.txt", f, "text/plain"))])
        assert resp.json()["skipped"] == expected

    def test_garbage_file_returns_200_with_error(self, client):
        resp = client.post("/import", files=[("files", ("bad.txt", b"garbage content", "text/plain"))])
        assert resp.status_code == 200
        assert len(resp.json()["errors"]) > 0

    def test_multiple_files_totals_are_summed(self, client):
        from parsers.ggpoker import GGPokerParser
        expected = len(GGPokerParser().parse_file(SAMPLE_FILE))
        with open(SAMPLE_FILE, "rb") as f1, open(SAMPLE_FILE, "rb") as f2:
            resp = client.post("/import", files=[
                ("files", ("a.txt", f1, "text/plain")),
                ("files", ("b.txt", f2, "text/plain")),
            ])
        data = resp.json()
        assert data["imported"] == expected      # second upload skipped
        assert data["skipped"] == expected       # first uploaded, second skipped

    def test_no_files_returns_422(self, client):
        resp = client.post("/import")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /{player}/stats
# ---------------------------------------------------------------------------

class TestPlayerStats:
    def test_returns_200(self, populated_client):
        resp = populated_client.get("/Hero/stats")
        assert resp.status_code == 200

    def test_has_required_fields(self, populated_client):
        data = populated_client.get("/Hero/stats").json()
        assert {"vpip", "pfr", "bb_per_100", "bb_per_100_adjusted", "hands"} <= data.keys()

    def test_hands_count_positive(self, populated_client):
        assert populated_client.get("/Hero/stats").json()["hands"] > 0

    def test_vpip_in_range(self, populated_client):
        assert 0 <= populated_client.get("/Hero/stats").json()["vpip"] <= 100

    def test_pfr_in_range(self, populated_client):
        assert 0 <= populated_client.get("/Hero/stats").json()["pfr"] <= 100

    def test_pfr_lte_vpip(self, populated_client):
        data = populated_client.get("/Hero/stats").json()
        assert data["pfr"] <= data["vpip"]

    def test_unknown_player_zero_hands(self, populated_client):
        assert populated_client.get("/NoSuchPlayer/stats").json()["hands"] == 0


# ---------------------------------------------------------------------------
# GET /{player}/hands
# ---------------------------------------------------------------------------

class TestPlayerHands:
    def test_returns_200(self, populated_client):
        assert populated_client.get("/Hero/hands").json() is not None

    def test_returns_hands_list(self, populated_client):
        data = populated_client.get("/Hero/hands").json()
        assert isinstance(data["hands"], list)

    def test_hand_count_consistent_with_stats(self, populated_client):
        stats = populated_client.get("/Hero/stats").json()
        # default page_size may be smaller, but total should match
        data = populated_client.get("/Hero/hands?page_size=500").json()
        assert data["total"] == stats["hands"]

    def test_hands_have_required_fields(self, populated_client):
        data = populated_client.get("/Hero/hands").json()
        required = {"hand_id", "played_at", "table_name", "game_type", "small_blind", "big_blind"}
        for hand in data["hands"]:
            assert required <= hand.keys()

    def test_pagination_no_overlap(self, populated_client):
        page1 = populated_client.get("/Hero/hands?page=1&page_size=5").json()["hands"]
        page2 = populated_client.get("/Hero/hands?page=2&page_size=5").json()["hands"]
        ids1 = {h["hand_id"] for h in page1}
        ids2 = {h["hand_id"] for h in page2}
        assert ids1.isdisjoint(ids2)

    def test_empty_db_returns_empty_list(self, client):
        data = client.get("/Hero/hands").json()
        assert data["hands"] == []
        assert data["total"] == 0
