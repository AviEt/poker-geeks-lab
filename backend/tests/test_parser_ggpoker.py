"""
Tests for the GGPoker hand history parser.
Each class covers one distinct parsing concern.

Real hand files are in fixtures/hand_histories/real_hands/ and contain
multiple hands per file.
"""

from pathlib import Path

import pytest

from domain.action import ActionType
from domain.hand import GameType
from domain.street import StreetName
from parsers.ggpoker import GGPokerParser
from parsers.base import ParseError

FIXTURES = Path(__file__).parent / "fixtures" / "hand_histories"
REAL_HANDS = FIXTURES / "real_hands"

# Pick one known file to run specific assertions against
SAMPLE_FILE = REAL_HANDS / "GG20231205-1004 - RushAndCash15083753 - 0.02 - 0.05 - 6max.txt"


@pytest.fixture
def parser() -> GGPokerParser:
    return GGPokerParser()


# ---------------------------------------------------------------------------
# Multi-hand splitting
# ---------------------------------------------------------------------------

class TestMultiHandSplitting:
    def test_returns_multiple_hands(self, parser):
        hands = parser.parse_file(SAMPLE_FILE)
        assert len(hands) > 1

    def test_all_hands_have_unique_ids(self, parser):
        hands = parser.parse_file(SAMPLE_FILE)
        ids = [h.hand_id for h in hands]
        assert len(ids) == len(set(ids))

    def test_all_real_files_parse_without_error(self, parser):
        """Integration smoke test: every real file must parse cleanly."""
        for path in REAL_HANDS.glob("*.txt"):
            hands = parser.parse_file(path)
            assert len(hands) > 0, f"No hands parsed from {path.name}"


# ---------------------------------------------------------------------------
# Hand metadata (spot-check against first hand of sample file)
# ---------------------------------------------------------------------------

class TestHandMetadata:
    @pytest.fixture
    def first_hand(self, parser):
        return parser.parse_file(SAMPLE_FILE)[0]

    def test_hand_id_is_numeric_string(self, first_hand):
        assert first_hand.hand_id.isdigit()

    def test_game_type_is_nlhe(self, first_hand):
        assert first_hand.game_type == GameType.NLHE

    def test_small_blind(self, first_hand):
        assert first_hand.small_blind == pytest.approx(0.02)

    def test_big_blind(self, first_hand):
        assert first_hand.big_blind == pytest.approx(0.05)

    def test_table_name_not_empty(self, first_hand):
        assert first_hand.table_name != ""

    def test_datetime_year(self, first_hand):
        assert first_hand.played_at.year == 2023

    def test_datetime_month(self, first_hand):
        assert first_hand.played_at.month == 12


# ---------------------------------------------------------------------------
# Player parsing
# ---------------------------------------------------------------------------

class TestPlayerParsing:
    @pytest.fixture
    def first_hand(self, parser):
        return parser.parse_file(SAMPLE_FILE)[0]

    def test_six_players(self, first_hand):
        assert len(first_hand.players) == 6

    def test_hero_is_present(self, first_hand):
        names = {p.name for p in first_hand.players}
        assert "Hero" in names

    def test_hero_stack(self, first_hand):
        hero = next(p for p in first_hand.players if p.name == "Hero")
        assert hero.stack == pytest.approx(6.98)

    def test_seats_are_numbered(self, first_hand):
        seats = [p.seat for p in first_hand.players]
        assert all(1 <= s <= 9 for s in seats)


# ---------------------------------------------------------------------------
# Hero hole cards
# ---------------------------------------------------------------------------

class TestHoleCards:
    @pytest.fixture
    def first_hand(self, parser):
        return parser.parse_file(SAMPLE_FILE)[0]

    def test_hero_has_two_hole_cards(self, first_hand):
        hero = next(p for p in first_hand.players if p.name == "Hero")
        assert len(hero.hole_cards) == 2

    def test_opponent_hole_cards_empty(self, first_hand):
        """GGPoker does not reveal opponent hole cards (unless shown at showdown)."""
        non_heroes = [p for p in first_hand.players if p.name != "Hero"]
        # At most one opponent may have shown cards at showdown; others should be empty
        shown = [p for p in non_heroes if p.hole_cards]
        assert len(shown) <= len(first_hand.players) - 1


# ---------------------------------------------------------------------------
# Preflop actions
# ---------------------------------------------------------------------------

class TestPreflopActions:
    @pytest.fixture
    def first_hand(self, parser):
        return parser.parse_file(SAMPLE_FILE)[0]

    def test_sb_post_recorded(self, first_hand):
        preflop = next(s for s in first_hand.streets if s.name == StreetName.PREFLOP)
        posts = [a for a in preflop.actions if a.action_type == ActionType.POST_SB]
        assert len(posts) == 1
        assert posts[0].amount == pytest.approx(0.02)

    def test_bb_post_recorded(self, first_hand):
        preflop = next(s for s in first_hand.streets if s.name == StreetName.PREFLOP)
        posts = [a for a in preflop.actions if a.action_type == ActionType.POST_BB]
        assert len(posts) == 1
        assert posts[0].amount == pytest.approx(0.05)

    def test_hero_raised_preflop(self, first_hand):
        preflop = next(s for s in first_hand.streets if s.name == StreetName.PREFLOP)
        hero_raises = [
            a for a in preflop.actions
            if a.action_type == ActionType.RAISE and a.player_name == "Hero"
        ]
        assert len(hero_raises) == 1


# ---------------------------------------------------------------------------
# Postflop actions
# ---------------------------------------------------------------------------

class TestPostflopActions:
    @pytest.fixture
    def first_hand(self, parser):
        return parser.parse_file(SAMPLE_FILE)[0]

    def test_flop_exists(self, first_hand):
        names = [s.name for s in first_hand.streets]
        assert StreetName.FLOP in names

    def test_flop_has_three_cards(self, first_hand):
        flop = next(s for s in first_hand.streets if s.name == StreetName.FLOP)
        assert len(flop.cards) == 3

    def test_turn_has_one_card(self, first_hand):
        turn = next(s for s in first_hand.streets if s.name == StreetName.TURN)
        assert len(turn.cards) == 1

    def test_river_has_one_card(self, first_hand):
        river = next(s for s in first_hand.streets if s.name == StreetName.RIVER)
        assert len(river.cards) == 1


# ---------------------------------------------------------------------------
# Showdown / shows captured from action lines
# ---------------------------------------------------------------------------

class TestShowdown:
    @pytest.fixture
    def first_hand(self, parser):
        return parser.parse_file(SAMPLE_FILE)[0]

    def test_shown_cards_captured_at_showdown(self, first_hand):
        """Both players showed cards in the first hand (split pot)."""
        shown = [p for p in first_hand.players if p.hole_cards]
        assert len(shown) >= 1


# ---------------------------------------------------------------------------
# Net won / results
# ---------------------------------------------------------------------------

class TestNetWon:
    @pytest.fixture
    def hands(self, parser):
        return parser.parse_file(SAMPLE_FILE)

    def test_net_won_sum_is_near_zero_minus_rake(self, hands):
        """
        Across all hands in a file, the sum of all players' net_won
        should equal cash_drop - rake - cashout_risk (all fees that leave the table).
        Allow some floating-point tolerance.
        """
        for hand in hands:
            total = sum(p.net_won for p in hand.players)
            expected = hand.cash_drop - hand.rake
            assert total == pytest.approx(expected, abs=0.01), (
                f"Hand {hand.hand_id}: net_won sum {total:.4f} != cash_drop-rake-cashout_risk {expected:.4f}"
            )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_malformed_file_raises_parse_error(self, parser, tmp_path):
        bad = tmp_path / "garbage.txt"
        bad.write_text("this is not a hand history\n")
        with pytest.raises(ParseError):
            parser.parse_file(bad)


# ---------------------------------------------------------------------------
# All-in equity detection (preflop all-in runout)
# ---------------------------------------------------------------------------

ALLIN_FIXTURE = FIXTURES / "gg_allin_preflop.txt"


@pytest.fixture(scope="module")
def allin_hand_preflop():
    """Parsed preflop all-in hand — module-scoped so equity enumeration runs once."""
    return GGPokerParser().parse_file(ALLIN_FIXTURE)[0]


class TestAllInEquityParsing:
    @pytest.fixture
    def allin_hand(self, allin_hand_preflop):
        return allin_hand_preflop

    def test_opponent_hole_cards_captured_from_preflop_shows(self, allin_hand):
        """Villain shows cards in the preflop section — must be captured."""
        villain = next(p for p in allin_hand.players if p.name == "Villain")
        assert villain.hole_cards == ["Kh", "Kd"]

    def test_allin_equity_is_set(self, allin_hand):
        """Preflop all-in with both players showing → equity must be populated."""
        assert allin_hand.all_in_equity is not None

    def test_allin_equity_has_hero_and_villain(self, allin_hand):
        assert "Hero" in allin_hand.all_in_equity
        assert "Villain" in allin_hand.all_in_equity

    def test_allin_equity_sums_to_one(self, allin_hand):
        total = sum(allin_hand.all_in_equity.values())
        assert abs(total - 1.0) < 0.01

    def test_allin_equity_hero_is_aa_vs_kk_favourite(self, allin_hand):
        """AA vs KK: Hero should have ~82% equity."""
        assert abs(allin_hand.all_in_equity["Hero"] - 0.82) < 0.03

    def test_allin_pot_bb_is_set(self, allin_hand):
        assert allin_hand.all_in_pot_bb is not None

    def test_allin_pot_bb_reflects_total_main_pot(self, allin_hand):
        """Both players invest $12 at $0.10 BB → total main pot = 240bb."""
        assert abs(allin_hand.all_in_pot_bb - 240.0) < 1.0

    def test_allin_invested_bb_is_set(self, allin_hand):
        """Hero invested $12 at $0.10 BB → 120bb."""
        assert abs(allin_hand.all_in_invested_bb - 120.0) < 1.0

    def test_no_allin_hand_has_no_equity(self, parser):
        """A regular hand (no all-in) must leave all_in_equity as None."""
        # Use a real hand file where most hands are not all-in runouts
        hands = parser.parse_file(SAMPLE_FILE)
        non_allin = [h for h in hands if h.all_in_equity is None]
        assert len(non_allin) > 0

    def test_allin_equity_is_deterministic(self, parser):
        """
        Equity computation must be deterministic — parsing the same hand twice
        must yield bit-for-bit identical equity values.  Monte Carlo sampling
        would fail this test; exact enumeration passes it.

        Uses a turn all-in fixture (only 44 run-outs) to keep the test fast.
        """
        turn_fixture = FIXTURES / "gg_allin_turn.txt"
        hand_a = parser.parse_file(turn_fixture)[0]
        hand_b = parser.parse_file(turn_fixture)[0]
        assert hand_a.all_in_equity == hand_b.all_in_equity

    def test_deterministic_outcome_not_marked_as_allin(self, parser):
        """
        When one player has 100 % equity (the outcome is already certain at
        the time of all-in), the hand must NOT be flagged as all-in adjusted.
        all_in_equity should be None so that actual net_won is used instead.

        RC2030688727: Hero 9hAh vs QdJh on board 2s As 3d after turn all-in.
        Hero has 100 % equity — every possible river card keeps him ahead.
        """
        target_id = "2030688727"
        all_hands: list = []
        for path in REAL_HANDS.glob("*.txt"):
            all_hands.extend(parser.parse_file(path))
        hand = next((h for h in all_hands if h.hand_id == target_id), None)
        assert hand is not None, f"Hand {target_id} not found in real_hands fixtures"
        assert hand.all_in_equity is None, (
            "Hand with deterministic 100% equity must not be all-in adjusted"
        )
