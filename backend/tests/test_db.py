"""
Tests for the database layer: ORM schema, HandRepository, and import use case.

All tests use SQLite in-memory — no PostgreSQL required.
"""

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from db.schema import ActionRow, Base, HandRow, PlayerRow, StreetRow
from db.repository import HandRepository
from app.import_hands import import_hands
from domain.action import Action, ActionType
from domain.hand import GameType, Hand
from domain.player import Player
from domain.street import Street, StreetName
from parsers.ggpoker import GGPokerParser

REAL_HANDS = Path(__file__).parent / "fixtures" / "hand_histories" / "real_hands"
SAMPLE_FILE = REAL_HANDS / "GG20231205-1004 - RushAndCash15083753 - 0.02 - 0.05 - 6max.txt"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def repo(session):
    return HandRepository(session)


# ---------------------------------------------------------------------------
# Minimal domain objects for unit tests
# ---------------------------------------------------------------------------

def _make_hand(hand_id: str = "99999") -> Hand:
    return Hand(
        hand_id=hand_id,
        game_type=GameType.NLHE,
        small_blind=0.02,
        big_blind=0.05,
        table_name="TestTable",
        played_at=datetime(2024, 1, 1, 12, 0, 0),
        hero_name="Hero",
        players=[
            Player(name="Hero", seat=1, stack=5.00, net_won=0.10),
            Player(name="Villain", seat=2, stack=5.00, net_won=-0.10),
        ],
        streets=[
            Street(name=StreetName.PREFLOP, actions=[
                Action("Hero", ActionType.POST_SB, 0.02),
                Action("Villain", ActionType.POST_BB, 0.05),
                Action("Hero", ActionType.CALL, 0.05),
                Action("Villain", ActionType.CHECK),
            ]),
            Street(name=StreetName.FLOP, cards=["Ah", "Kd", "2c"], actions=[
                Action("Hero", ActionType.BET, 0.08),
                Action("Villain", ActionType.FOLD),
            ]),
        ],
        pot=0.10,
        rake=0.0,
        cash_drop=0.0,
    )


# ---------------------------------------------------------------------------
# Schema — tables are created
# ---------------------------------------------------------------------------

class TestSchema:
    def test_hands_table_exists(self, engine):
        with engine.connect() as conn:
            tables = {r[0] for r in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))}
        assert "hands" in tables

    def test_players_table_exists(self, engine):
        with engine.connect() as conn:
            tables = {r[0] for r in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))}
        assert "players" in tables

    def test_streets_table_exists(self, engine):
        with engine.connect() as conn:
            tables = {r[0] for r in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))}
        assert "streets" in tables

    def test_actions_table_exists(self, engine):
        with engine.connect() as conn:
            tables = {r[0] for r in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))}
        assert "actions" in tables


# ---------------------------------------------------------------------------
# HandRepository — save and retrieve
# ---------------------------------------------------------------------------

class TestHandRepository:
    def test_save_hand_returns_db_id(self, repo):
        db_id = repo.save_hand(_make_hand("11111"))
        assert isinstance(db_id, int) and db_id > 0

    def test_get_hand_by_hand_id(self, repo):
        repo.save_hand(_make_hand("22222"))
        row = repo.get_hand("22222")
        assert row is not None
        assert row.hand_id == "22222"

    def test_get_hand_returns_none_for_missing(self, repo):
        assert repo.get_hand("nonexistent") is None

    def test_saved_hand_blinds(self, repo):
        repo.save_hand(_make_hand("33333"))
        row = repo.get_hand("33333")
        assert row.small_blind == pytest.approx(0.02)
        assert row.big_blind == pytest.approx(0.05)

    def test_saved_hand_rake_and_cash_drop(self, repo):
        hand = _make_hand("44444")
        hand.rake = 0.05
        hand.cash_drop = 0.50
        repo.save_hand(hand)
        row = repo.get_hand("44444")
        assert row.rake == pytest.approx(0.05)
        assert row.cash_drop == pytest.approx(0.50)

    def test_duplicate_hand_id_returns_none(self, repo):
        hand = _make_hand("55555")
        repo.save_hand(hand)
        result = repo.save_hand(hand)
        assert result is None

    def test_duplicate_does_not_create_extra_row(self, repo, session):
        hand = _make_hand("66666")
        repo.save_hand(hand)
        repo.save_hand(hand)
        count = session.query(HandRow).filter_by(hand_id="66666").count()
        assert count == 1


# ---------------------------------------------------------------------------
# Players linked to their hand
# ---------------------------------------------------------------------------

class TestPlayerRepository:
    def test_players_saved_with_hand(self, repo, session):
        repo.save_hand(_make_hand("77777"))
        rows = (
            session.query(PlayerRow)
            .join(HandRow)
            .filter(HandRow.hand_id == "77777")
            .all()
        )
        assert len(rows) == 2

    def test_player_names_match(self, repo, session):
        repo.save_hand(_make_hand("88888"))
        rows = (
            session.query(PlayerRow)
            .join(HandRow)
            .filter(HandRow.hand_id == "88888")
            .all()
        )
        assert {r.name for r in rows} == {"Hero", "Villain"}

    def test_player_net_won_stored(self, repo, session):
        repo.save_hand(_make_hand("99991"))
        hero = (
            session.query(PlayerRow)
            .join(HandRow)
            .filter(HandRow.hand_id == "99991", PlayerRow.name == "Hero")
            .one()
        )
        assert hero.net_won == pytest.approx(0.10)

    def test_hero_name_stored_on_hand(self, repo):
        repo.save_hand(_make_hand("99992"))
        row = repo.get_hand("99992")
        assert row.hero_name == "Hero"


# ---------------------------------------------------------------------------
# Streets and actions linked to their hand
# ---------------------------------------------------------------------------

class TestStreetRepository:
    def test_streets_saved_in_order(self, repo, session):
        repo.save_hand(_make_hand("10001"))
        rows = (
            session.query(StreetRow)
            .join(HandRow)
            .filter(HandRow.hand_id == "10001")
            .order_by(StreetRow.street_order)
            .all()
        )
        assert [r.name for r in rows] == ["preflop", "flop"]

    def test_flop_cards_stored(self, repo, session):
        repo.save_hand(_make_hand("10002"))
        flop = (
            session.query(StreetRow)
            .join(HandRow)
            .filter(HandRow.hand_id == "10002", StreetRow.name == "flop")
            .one()
        )
        assert flop.cards == "Ah Kd 2c"

    def test_preflop_action_count(self, repo, session):
        repo.save_hand(_make_hand("10003"))
        preflop = (
            session.query(StreetRow)
            .join(HandRow)
            .filter(HandRow.hand_id == "10003", StreetRow.name == "preflop")
            .one()
        )
        actions = session.query(ActionRow).filter_by(street_id=preflop.id).all()
        assert len(actions) == 4  # post_sb, post_bb, call, check

    def test_action_type_and_amount_stored(self, repo, session):
        repo.save_hand(_make_hand("10004"))
        preflop = (
            session.query(StreetRow)
            .join(HandRow)
            .filter(HandRow.hand_id == "10004", StreetRow.name == "preflop")
            .one()
        )
        post_sb = (
            session.query(ActionRow)
            .filter_by(street_id=preflop.id, action_type="post_sb")
            .one()
        )
        assert post_sb.player_name == "Hero"
        assert post_sb.amount == pytest.approx(0.02)


# ---------------------------------------------------------------------------
# All-in equity storage and round-trip
# ---------------------------------------------------------------------------

class TestAllInEquityStorage:
    def test_save_hand_with_equity_persists_json(self, repo):
        hand = _make_hand("AE001")
        hand.all_in_equity = {"Hero": 0.82, "Villain": 0.18}
        hand.all_in_pot_bb = 120.0
        repo.save_hand(hand)
        row = repo.get_hand("AE001")
        assert row.allin_equity_json is not None
        assert row.allin_pot_bb == pytest.approx(120.0)

    def test_save_hand_equity_roundtrips_correctly(self, repo):
        from app.compute_stats import _to_domain_hand
        hand = _make_hand("AE002")
        hand.all_in_equity = {"Hero": 0.75, "Villain": 0.25}
        hand.all_in_pot_bb = 200.0
        repo.save_hand(hand)
        row = repo.get_hand("AE002")
        reconstructed = _to_domain_hand(row)
        assert reconstructed.all_in_equity == pytest.approx({"Hero": 0.75, "Villain": 0.25})
        assert reconstructed.all_in_pot_bb == pytest.approx(200.0)

    def test_save_hand_without_equity_stores_null(self, repo):
        hand = _make_hand("AE003")
        repo.save_hand(hand)
        row = repo.get_hand("AE003")
        assert row.allin_equity_json is None
        assert row.allin_pot_bb is None

    def test_reconstructed_hand_without_equity_has_none(self, repo):
        from app.compute_stats import _to_domain_hand
        hand = _make_hand("AE004")
        repo.save_hand(hand)
        row = repo.get_hand("AE004")
        reconstructed = _to_domain_hand(row)
        assert reconstructed.all_in_equity is None
        assert reconstructed.all_in_pot_bb is None


# ---------------------------------------------------------------------------
# Import use case
# ---------------------------------------------------------------------------

class TestImportUseCase:
    def test_imported_count_matches_parser(self, engine):
        expected = len(GGPokerParser().parse_file(SAMPLE_FILE))
        result = import_hands(SAMPLE_FILE, engine=engine)
        assert result["imported"] == expected

    def test_reimport_imports_zero(self, engine):
        import_hands(SAMPLE_FILE, engine=engine)
        result = import_hands(SAMPLE_FILE, engine=engine)
        assert result["imported"] == 0

    def test_reimport_skipped_count_matches_parser(self, engine):
        expected = len(GGPokerParser().parse_file(SAMPLE_FILE))
        import_hands(SAMPLE_FILE, engine=engine)
        result = import_hands(SAMPLE_FILE, engine=engine)
        assert result["skipped"] == expected

    def test_first_import_no_skips_no_errors(self, engine):
        result = import_hands(SAMPLE_FILE, engine=engine)
        assert result["skipped"] == 0
        assert result["errors"] == []
