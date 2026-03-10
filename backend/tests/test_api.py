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

    def test_has_new_xs_fields(self, populated_client):
        data = populated_client.get("/Hero/stats").json()
        assert {"amount_won", "dollar_per_100", "saw_flop", "saw_turn", "saw_river"} <= data.keys()

    def test_saw_flop_in_range(self, populated_client):
        assert 0 <= populated_client.get("/Hero/stats").json()["saw_flop"] <= 100

    def test_saw_turn_in_range(self, populated_client):
        assert 0 <= populated_client.get("/Hero/stats").json()["saw_turn"] <= 100

    def test_saw_river_in_range(self, populated_client):
        assert 0 <= populated_client.get("/Hero/stats").json()["saw_river"] <= 100

    def test_saw_flop_gte_saw_turn(self, populated_client):
        data = populated_client.get("/Hero/stats").json()
        assert data["saw_flop"] >= data["saw_turn"]

    def test_saw_turn_gte_saw_river(self, populated_client):
        data = populated_client.get("/Hero/stats").json()
        assert data["saw_turn"] >= data["saw_river"]

    def test_amount_won_is_numeric(self, populated_client):
        data = populated_client.get("/Hero/stats").json()
        assert isinstance(data["amount_won"], (int, float))

    def test_dollar_per_100_is_numeric(self, populated_client):
        data = populated_client.get("/Hero/stats").json()
        assert isinstance(data["dollar_per_100"], (int, float))

    def test_has_s_effort_fields(self, populated_client):
        data = populated_client.get("/Hero/stats").json()
        expected = {
            "rfi", "limp", "call_open", "three_bet", "four_bet",
            "fold_to_3bet", "fold_to_4bet", "call_3bet",
            "attempt_steal", "fold_bb_to_steal", "fold_sb_to_steal",
            "wtsd", "wsd", "std_dev",
        }
        assert expected <= data.keys()

    def test_s_effort_percentages_in_range(self, populated_client):
        data = populated_client.get("/Hero/stats").json()
        for key in ("rfi", "three_bet", "attempt_steal", "wtsd", "wsd"):
            assert 0 <= data[key] <= 100, f"{key} out of range"

    def test_std_dev_non_negative(self, populated_client):
        assert populated_client.get("/Hero/stats").json()["std_dev"] >= 0

    def test_wtsd_lte_saw_flop(self, populated_client):
        data = populated_client.get("/Hero/stats").json()
        assert data["wtsd"] <= data["saw_flop"]


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

    def test_hands_have_extended_fields(self, populated_client):
        data = populated_client.get("/Hero/hands").json()
        extended = {"hero_position", "hero_hole_cards", "flop", "turn", "river", "net_won"}
        for hand in data["hands"]:
            assert extended <= hand.keys()

    def test_hero_position_present(self, populated_client):
        data = populated_client.get("/Hero/hands").json()
        positions_seen = [h["hero_position"] for h in data["hands"] if h["hero_position"]]
        assert len(positions_seen) > 0

    def test_hero_hole_cards_present_for_hero(self, populated_client):
        data = populated_client.get("/Hero/hands").json()
        cards_seen = [h["hero_hole_cards"] for h in data["hands"] if h["hero_hole_cards"]]
        assert len(cards_seen) > 0

    def test_board_cards_present_for_postflop_hands(self, populated_client):
        data = populated_client.get("/Hero/hands?page_size=500").json()
        flops = [h["flop"] for h in data["hands"] if h["flop"]]
        assert len(flops) > 0

    def test_hands_include_bb_per_100(self, populated_client):
        data = populated_client.get("/Hero/hands?page_size=500").json()
        for hand in data["hands"]:
            assert "bb_per_100" in hand
            expected = round(hand["net_won"] / hand["big_blind"] * 100, 2)
            assert hand["bb_per_100"] == pytest.approx(expected, abs=0.01)

    def test_hands_include_bb_per_100_adj(self, populated_client):
        data = populated_client.get("/Hero/hands").json()
        for hand in data["hands"]:
            assert "bb_per_100_adj" in hand

    def test_hands_include_pot_won(self, populated_client):
        data = populated_client.get("/Hero/hands?page_size=500").json()
        for hand in data["hands"]:
            assert "pot_won" in hand
            assert hand["pot_won"] >= 0

    def test_pot_won_equals_pot_won_after_rake_plus_rake(self, populated_client):
        data = populated_client.get("/Hero/hands?page_size=500").json()
        winners = [h for h in data["hands"] if h["pot_won_after_rake_usd"] > 0]
        assert len(winners) > 0
        for hand in winners:
            assert hand["pot_won"] == pytest.approx(
                hand["pot_won_after_rake_usd"] + hand["rake_usd"], abs=0.001
            )

    def test_hands_include_rake_usd(self, populated_client):
        data = populated_client.get("/Hero/hands").json()
        for hand in data["hands"]:
            assert "rake_usd" in hand
            assert hand["rake_usd"] >= 0

    def test_hands_include_rake_bb(self, populated_client):
        data = populated_client.get("/Hero/hands?page_size=500").json()
        for hand in data["hands"]:
            assert "rake_bb" in hand
            expected = round(hand["rake_usd"] / hand["big_blind"], 4)
            assert hand["rake_bb"] == pytest.approx(expected, abs=0.0001)

    def test_hands_include_pot_won_after_rake_usd(self, populated_client):
        data = populated_client.get("/Hero/hands").json()
        for hand in data["hands"]:
            assert "pot_won_after_rake_usd" in hand
            assert hand["pot_won_after_rake_usd"] >= 0

    def test_hands_include_pot_won_after_rake_bb100(self, populated_client):
        data = populated_client.get("/Hero/hands?page_size=500").json()
        for hand in data["hands"]:
            assert "pot_won_after_rake_bb100" in hand
            expected = round(hand["pot_won_after_rake_usd"] / hand["big_blind"] * 100, 2)
            assert hand["pot_won_after_rake_bb100"] == pytest.approx(expected, abs=0.01)


# ---------------------------------------------------------------------------
# GET /{player}/hands/{hand_id}
# ---------------------------------------------------------------------------

class TestHandDetail:
    def test_returns_200(self, populated_client):
        hands = populated_client.get("/Hero/hands").json()["hands"]
        hid = hands[0]["hand_id"]
        resp = populated_client.get(f"/Hero/hands/{hid}")
        assert resp.status_code == 200

    def test_has_required_fields(self, populated_client):
        hands = populated_client.get("/Hero/hands").json()["hands"]
        hid = hands[0]["hand_id"]
        data = populated_client.get(f"/Hero/hands/{hid}").json()
        required = {"hand_id", "played_at", "table_name", "game_type", "players", "streets", "pot", "rake"}
        assert required <= data.keys()

    def test_streets_contain_actions(self, populated_client):
        hands = populated_client.get("/Hero/hands").json()["hands"]
        hid = hands[0]["hand_id"]
        data = populated_client.get(f"/Hero/hands/{hid}").json()
        assert len(data["streets"]) >= 1
        preflop = data["streets"][0]
        assert preflop["name"] == "preflop"
        assert len(preflop["actions"]) > 0

    def test_actions_have_required_fields(self, populated_client):
        hands = populated_client.get("/Hero/hands").json()["hands"]
        hid = hands[0]["hand_id"]
        data = populated_client.get(f"/Hero/hands/{hid}").json()
        for street in data["streets"]:
            for action in street["actions"]:
                assert {"player", "action", "amount", "is_all_in"} <= action.keys()

    def test_players_have_required_fields(self, populated_client):
        hands = populated_client.get("/Hero/hands").json()["hands"]
        hid = hands[0]["hand_id"]
        data = populated_client.get(f"/Hero/hands/{hid}").json()
        for p in data["players"]:
            assert {"name", "seat", "stack", "position", "hole_cards", "net_won"} <= p.keys()

    def test_404_for_missing_hand(self, populated_client):
        resp = populated_client.get("/Hero/hands/99999999")
        assert resp.status_code == 404

    def test_404_for_wrong_player(self, populated_client):
        hands = populated_client.get("/Hero/hands").json()["hands"]
        hid = hands[0]["hand_id"]
        resp = populated_client.get(f"/NoSuchPlayer/hands/{hid}")
        assert resp.status_code == 404
