"""
Tests for the PokerStars hand history parser.
Each class covers one distinct parsing concern.
"""

from pathlib import Path

import pytest

from domain.action import ActionType
from domain.hand import GameType
from domain.street import StreetName
from parsers.pokerstars import PokerStarsParser, ParseError

FIXTURES = Path(__file__).parent / "fixtures" / "hand_histories"


@pytest.fixture
def parser() -> PokerStarsParser:
    return PokerStarsParser()


def parse_one(parser: PokerStarsParser, path) -> object:
    """Unwrap the single hand returned from a PokerStars file."""
    return parser.parse_file(path)[0]


# ---------------------------------------------------------------------------
# Hand metadata
# ---------------------------------------------------------------------------

class TestHandMetadata:
    def test_hand_id(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        assert hand.hand_id == "220001000001"

    def test_game_type_is_nlhe(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        assert hand.game_type == GameType.NLHE

    def test_blinds(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        assert hand.small_blind == 0.01
        assert hand.big_blind == 0.02

    def test_currency(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        assert hand.currency == "USD"

    def test_table_name(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        assert hand.table_name == "Altair II"

    def test_datetime_parsed(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        assert hand.played_at.year == 2024
        assert hand.played_at.month == 1
        assert hand.played_at.day == 7


# ---------------------------------------------------------------------------
# Player parsing
# ---------------------------------------------------------------------------

class TestPlayerParsing:
    def test_player_count(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        assert len(hand.players) == 6

    def test_player_names(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        names = {p.name for p in hand.players}
        assert "Hero" in names
        assert "BTNPlayer" in names
        assert "SBPlayer" in names
        assert "BBPlayer" in names

    def test_player_stacks(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        hero = next(p for p in hand.players if p.name == "Hero")
        assert hero.stack == 2.00

    def test_player_seats(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        hero = next(p for p in hand.players if p.name == "Hero")
        assert hero.seat == 6

    def test_hero_hole_cards(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        hero = next(p for p in hand.players if p.name == "Hero")
        assert set(hero.hole_cards) == {"Ah", "Kd"}


# ---------------------------------------------------------------------------
# Preflop actions
# ---------------------------------------------------------------------------

class TestPreflopActions:
    def test_sb_post_recorded(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        preflop = next(s for s in hand.streets if s.name == StreetName.PREFLOP)
        sb_post = next(
            a for a in preflop.actions
            if a.action_type == ActionType.POST_SB
        )
        assert sb_post.player_name == "SBPlayer"
        assert sb_post.amount == pytest.approx(0.01)

    def test_bb_post_recorded(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        preflop = next(s for s in hand.streets if s.name == StreetName.PREFLOP)
        bb_post = next(
            a for a in preflop.actions
            if a.action_type == ActionType.POST_BB
        )
        assert bb_post.player_name == "BBPlayer"
        assert bb_post.amount == pytest.approx(0.02)

    def test_raise_recorded(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        preflop = next(s for s in hand.streets if s.name == StreetName.PREFLOP)
        raise_action = next(
            a for a in preflop.actions
            if a.action_type == ActionType.RAISE and a.player_name == "Hero"
        )
        assert raise_action.amount == pytest.approx(0.06)

    def test_folds_recorded(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        preflop = next(s for s in hand.streets if s.name == StreetName.PREFLOP)
        folds = [a for a in preflop.actions if a.action_type == ActionType.FOLD]
        fold_names = {a.player_name for a in folds}
        assert "UTGPlayer" in fold_names
        assert "HJPlayer" in fold_names
        assert "BTNPlayer" in fold_names
        assert "SBPlayer" in fold_names
        assert "BBPlayer" in fold_names


# ---------------------------------------------------------------------------
# Postflop actions
# ---------------------------------------------------------------------------

class TestPostflopActions:
    def test_flop_street_exists(self, parser):
        hand = parse_one(parser, FIXTURES / "limp_bb_checks.txt")
        street_names = [s.name for s in hand.streets]
        assert StreetName.FLOP in street_names

    def test_flop_board_cards(self, parser):
        hand = parse_one(parser, FIXTURES / "limp_bb_checks.txt")
        flop = next(s for s in hand.streets if s.name == StreetName.FLOP)
        assert set(flop.cards) == {"Ks", "9h", "3d"}

    def test_turn_board_card(self, parser):
        hand = parse_one(parser, FIXTURES / "limp_bb_checks.txt")
        turn = next(s for s in hand.streets if s.name == StreetName.TURN)
        assert "2h" in turn.cards

    def test_river_board_card(self, parser):
        hand = parse_one(parser, FIXTURES / "limp_bb_checks.txt")
        river = next(s for s in hand.streets if s.name == StreetName.RIVER)
        assert "5c" in river.cards

    def test_check_actions_on_flop(self, parser):
        hand = parse_one(parser, FIXTURES / "limp_bb_checks.txt")
        flop = next(s for s in hand.streets if s.name == StreetName.FLOP)
        checks = [a for a in flop.actions if a.action_type == ActionType.CHECK]
        assert len(checks) == 2


# ---------------------------------------------------------------------------
# Showdown and results
# ---------------------------------------------------------------------------

class TestShowdownAndResults:
    def test_showdown_hole_cards_captured(self, parser):
        hand = parse_one(parser, FIXTURES / "allin_preflop.txt")
        bb_player = next(p for p in hand.players if p.name == "BBPlayer")
        assert set(bb_player.hole_cards) == {"Kh", "Kd"}

    def test_winner_net_won(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        hero = next(p for p in hand.players if p.name == "Hero")
        # Hero raises to $0.06, $0.04 uncalled returned, $0.05 collected
        # net = $0.05 collected + $0.04 uncalled - $0.06 invested = $0.03
        assert hero.net_won == pytest.approx(0.03)

    def test_loser_net_won(self, parser):
        hand = parse_one(parser, FIXTURES / "allin_preflop.txt")
        bb_player = next(p for p in hand.players if p.name == "BBPlayer")
        assert bb_player.net_won < 0

    def test_all_in_flagged(self, parser):
        hand = parse_one(parser, FIXTURES / "allin_preflop.txt")
        preflop = next(s for s in hand.streets if s.name == StreetName.PREFLOP)
        all_in_actions = [a for a in preflop.actions if a.is_all_in]
        assert len(all_in_actions) >= 1


# ---------------------------------------------------------------------------
# Hand ID uniqueness (duplicate detection support)
# ---------------------------------------------------------------------------

class TestHandIdStability:
    def test_same_file_same_hand_id(self, parser):
        hand1 = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        hand2 = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        assert hand1.hand_id == hand2.hand_id

    def test_different_files_different_hand_ids(self, parser):
        hand1 = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        hand2 = parse_one(parser, FIXTURES / "walk_bb_wins.txt")
        assert hand1.hand_id != hand2.hand_id


# ---------------------------------------------------------------------------
# Pot won tracking
# ---------------------------------------------------------------------------

class TestPotWon:
    def test_winner_pot_won_after_rake_equals_collected(self, parser):
        # Hero collects $0.05 from pot; uncalled $0.04 returned separately
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        hero = next(p for p in hand.players if p.name == "Hero")
        assert hero.pot_won_after_rake == pytest.approx(0.05)

    def test_uncalled_bet_not_included_in_pot_won(self, parser):
        # pot_won_after_rake must NOT include the $0.04 uncalled bet returned to Hero
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        hero = next(p for p in hand.players if p.name == "Hero")
        assert hero.pot_won_after_rake == pytest.approx(0.05)   # not 0.09
        assert hero.pot_won_after_rake != pytest.approx(0.09)

    def test_loser_pot_won_after_rake_is_zero(self, parser):
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        bb_player = next(p for p in hand.players if p.name == "BBPlayer")
        assert bb_player.pot_won_after_rake == pytest.approx(0.0)

    def test_pot_won_after_rake_plus_rake_equals_total_pot(self, parser):
        # In a single-winner hand: collected + rake == total pot
        hand = parse_one(parser, FIXTURES / "basic_raise_and_win.txt")
        hero = next(p for p in hand.players if p.name == "Hero")
        assert hero.pot_won_after_rake + hand.rake == pytest.approx(hand.pot)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_malformed_file_raises_parse_error(self, parser, tmp_path):
        bad_file = tmp_path / "garbage.txt"
        bad_file.write_text("this is not a hand history\n")
        with pytest.raises(ParseError):
            parser.parse_file(bad_file)
