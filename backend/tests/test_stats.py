"""
Tests for domain/stats.py — all stat computations.
All tests use manually constructed Hand objects; no DB, no file I/O.

Stat definitions (source: PokerTracker4 / Hold'em Manager):
  VPIP  = voluntary preflop entries / hands_dealt
  PFR   = preflop raises / hands_dealt
  BB/100 = net_bb_won / hands * 100
  BB/100 adj = equity-adjusted net_bb_won / hands * 100 (all-in, cards to come)

A walk where Hero IS the BB is EXCLUDED from the VPIP/PFR denominator (PT4
definition) — Hero had no voluntary preflop decision. Walks where Hero is not
the BB still count in the denominator (Hero made a real decision to fold).
"""

from datetime import datetime

import pytest

from domain.action import Action, ActionType
from domain.hand import Hand, GameType
from domain.player import Player, Position
from domain.stats import compute_stats, StatLine, PlayerStats
from domain.street import Street, StreetName


def make_hand_with_streets(
    hand_id: str,
    players: list[Player],
    streets: list[Street],
    big_blind: float = 0.02,
    is_walk: bool = False,
) -> Hand:
    return Hand(
        hand_id=hand_id,
        game_type=GameType.NLHE,
        small_blind=big_blind / 2,
        big_blind=big_blind,
        table_name="TestTable",
        played_at=datetime(2024, 1, 1),
        players=players,
        streets=streets,
        is_walk=is_walk,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_hand(
    hand_id: str,
    players: list[Player],
    preflop_actions: list[Action],
    big_blind: float = 0.02,
    is_walk: bool = False,
) -> Hand:
    preflop = Street(name=StreetName.PREFLOP, actions=preflop_actions)
    return Hand(
        hand_id=hand_id,
        game_type=GameType.NLHE,
        small_blind=big_blind / 2,
        big_blind=big_blind,
        table_name="TestTable",
        played_at=datetime(2024, 1, 1),
        players=players,
        streets=[preflop],
        is_walk=is_walk,
    )


def make_player(name: str, net_won: float = 0.0) -> Player:
    return Player(name=name, seat=1, stack=2.00, net_won=net_won)


# ---------------------------------------------------------------------------
# StatLine
# ---------------------------------------------------------------------------

class TestStatLine:
    def test_percentage_when_nonzero(self):
        stat = StatLine(count=3, total=10)
        assert stat.percentage == pytest.approx(30.0)

    def test_percentage_when_zero_total(self):
        stat = StatLine(count=0, total=0)
        assert stat.percentage == 0.0

    def test_fraction_attributes(self):
        stat = StatLine(count=2, total=8)
        assert stat.count == 2
        assert stat.total == 8


# ---------------------------------------------------------------------------
# VPIP
# ---------------------------------------------------------------------------

class TestVPIP:
    def test_raise_preflop_counts_as_vpip(self):
        player = make_player("Hero")
        hand = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("BB", ActionType.POST_BB, 0.02),
                Action("Hero", ActionType.RAISE, 0.06),
            ],
        )
        stats = compute_stats([hand], "Hero")
        assert stats.vpip.count == 1
        assert stats.vpip.total == 1
        assert stats.vpip.percentage == pytest.approx(100.0)

    def test_call_preflop_counts_as_vpip(self):
        player = make_player("Hero")
        hand = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("BB", ActionType.POST_BB, 0.02),
                Action("Hero", ActionType.CALL, 0.02),
            ],
        )
        stats = compute_stats([hand], "Hero")
        assert stats.vpip.count == 1
        assert stats.vpip.percentage == pytest.approx(100.0)

    def test_limp_counts_as_vpip(self):
        """Calling the BB (limping) counts as VPIP."""
        player = make_player("Hero")
        hand = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("Hero", ActionType.POST_BB, 0.02),  # Hero is UTG, limps
                Action("Hero", ActionType.CALL, 0.02),
            ],
        )
        stats = compute_stats([hand], "Hero")
        assert stats.vpip.count == 1

    def test_posting_bb_and_folding_is_not_vpip(self):
        player = make_player("Hero")
        hand = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("Hero", ActionType.POST_BB, 0.02),
                Action("UTG", ActionType.RAISE, 0.06),
                Action("Hero", ActionType.FOLD),
            ],
        )
        stats = compute_stats([hand], "Hero")
        assert stats.vpip.count == 0
        assert stats.vpip.total == 1
        assert stats.vpip.percentage == pytest.approx(0.0)

    def test_posting_sb_and_folding_is_not_vpip(self):
        player = make_player("Hero")
        hand = make_hand(
            "1", [player],
            preflop_actions=[
                Action("Hero", ActionType.POST_SB, 0.01),
                Action("BB", ActionType.POST_BB, 0.02),
                Action("UTG", ActionType.RAISE, 0.06),
                Action("Hero", ActionType.FOLD),
            ],
        )
        stats = compute_stats([hand], "Hero")
        assert stats.vpip.count == 0
        assert stats.vpip.percentage == pytest.approx(0.0)

    def test_posting_bb_and_checking_after_limpers_is_not_vpip(self):
        """BB checks their option after everyone limped — not a voluntary action."""
        player = make_player("Hero")
        hand = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("Hero", ActionType.POST_BB, 0.02),
                Action("UTG", ActionType.CALL, 0.02),
                Action("Hero", ActionType.CHECK),
            ],
        )
        stats = compute_stats([hand], "Hero")
        assert stats.vpip.count == 0
        assert stats.vpip.total == 1
        assert stats.vpip.percentage == pytest.approx(0.0)

    def test_bb_walk_excluded_from_denominator(self):
        """
        PT4 definition: a walk where Hero IS the BB is excluded from the VPIP
        denominator — Hero had no opportunity to voluntarily act.
        Walks where Hero is not the BB (Hero folded preflop) still count.
        """
        player = make_player("Hero")
        walk_hand = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("Hero", ActionType.POST_BB, 0.02),
            ],
            is_walk=True,
        )
        # A second normal hand where Hero folds
        normal_hand = make_hand(
            "2", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("BB", ActionType.POST_BB, 0.02),
                Action("Hero", ActionType.FOLD),
            ],
        )
        stats = compute_stats([walk_hand, normal_hand], "Hero")
        # BB walk excluded → only the normal fold hand counts in denominator
        assert stats.vpip.total == 1
        assert stats.vpip.count == 0

    def test_vpip_percentage_across_multiple_hands(self):
        player = make_player("Hero")
        enters = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("BB", ActionType.POST_BB, 0.02),
                Action("Hero", ActionType.RAISE, 0.06),
            ],
        )
        folds = make_hand(
            "2", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("BB", ActionType.POST_BB, 0.02),
                Action("Hero", ActionType.FOLD),
            ],
        )
        stats = compute_stats([enters, folds], "Hero")
        assert stats.vpip.count == 1
        assert stats.vpip.total == 2
        assert stats.vpip.percentage == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# PFR
# ---------------------------------------------------------------------------

class TestPFR:
    def test_raise_preflop_counts_as_pfr(self):
        player = make_player("Hero")
        hand = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("BB", ActionType.POST_BB, 0.02),
                Action("Hero", ActionType.RAISE, 0.06),
            ],
        )
        stats = compute_stats([hand], "Hero")
        assert stats.pfr.count == 1
        assert stats.pfr.total == 1
        assert stats.pfr.percentage == pytest.approx(100.0)

    def test_call_preflop_is_not_pfr(self):
        player = make_player("Hero")
        hand = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("BB", ActionType.POST_BB, 0.02),
                Action("Hero", ActionType.CALL, 0.02),
            ],
        )
        stats = compute_stats([hand], "Hero")
        assert stats.pfr.count == 0
        assert stats.pfr.percentage == pytest.approx(0.0)

    def test_fold_preflop_is_not_pfr(self):
        player = make_player("Hero")
        hand = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("BB", ActionType.POST_BB, 0.02),
                Action("Hero", ActionType.FOLD),
            ],
        )
        stats = compute_stats([hand], "Hero")
        assert stats.pfr.count == 0
        assert stats.pfr.percentage == pytest.approx(0.0)

    def test_bb_walk_excluded_from_pfr_denominator(self):
        """
        PT4 definition: a walk where Hero IS the BB is excluded from the PFR
        denominator — Hero had no opportunity to raise.
        """
        player = make_player("Hero")
        walk_hand = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("Hero", ActionType.POST_BB, 0.02),
            ],
            is_walk=True,
        )
        stats = compute_stats([walk_hand], "Hero")
        assert stats.pfr.total == 0
        assert stats.pfr.count == 0

    def test_pfr_percentage_across_multiple_hands(self):
        player = make_player("Hero")
        raises = make_hand(
            "1", [player],
            preflop_actions=[
                Action("SB", ActionType.POST_SB, 0.01),
                Action("BB", ActionType.POST_BB, 0.02),
                Action("Hero", ActionType.RAISE, 0.06),
            ],
        )
        folds1 = make_hand(
            "2", [player],
            preflop_actions=[Action("SB", ActionType.POST_SB, 0.01),
                             Action("BB", ActionType.POST_BB, 0.02),
                             Action("Hero", ActionType.FOLD)],
        )
        folds2 = make_hand(
            "3", [player],
            preflop_actions=[Action("SB", ActionType.POST_SB, 0.01),
                             Action("BB", ActionType.POST_BB, 0.02),
                             Action("Hero", ActionType.FOLD)],
        )
        folds3 = make_hand(
            "4", [player],
            preflop_actions=[Action("SB", ActionType.POST_SB, 0.01),
                             Action("BB", ActionType.POST_BB, 0.02),
                             Action("Hero", ActionType.FOLD)],
        )
        stats = compute_stats([raises, folds1, folds2, folds3], "Hero")
        assert stats.pfr.count == 1
        assert stats.pfr.total == 4
        assert stats.pfr.percentage == pytest.approx(25.0)


# ---------------------------------------------------------------------------
# BB/100
# ---------------------------------------------------------------------------

class TestBB100:
    def test_win_one_hand(self):
        """Win 20bb in a $0.01/$0.02 game → net_won = $0.40 → BB/100 = +2000."""
        player = make_player("Hero", net_won=0.40)
        hand = make_hand("1", [player], [], big_blind=0.02)
        stats = compute_stats([hand], "Hero")
        assert stats.bb_per_100 == pytest.approx(2000.0)

    def test_lose_one_hand(self):
        player = make_player("Hero", net_won=-1.00)
        hand = make_hand("1", [player], [], big_blind=0.02)
        stats = compute_stats([hand], "Hero")
        assert stats.bb_per_100 == pytest.approx(-5000.0)

    def test_breakeven_two_hands(self):
        player_win = make_player("Hero", net_won=0.20)
        player_lose = make_player("Hero", net_won=-0.20)
        hand1 = make_hand("1", [player_win], [], big_blind=0.02)
        hand2 = make_hand("2", [player_lose], [], big_blind=0.02)
        stats = compute_stats([hand1, hand2], "Hero")
        assert stats.bb_per_100 == pytest.approx(0.0)

    def test_scales_correctly_over_100_hands(self):
        """Win 0.10 ($5bb) per hand over 100 hands → BB/100 = +5."""
        hands = []
        for i in range(100):
            p = make_player("Hero", net_won=0.10)
            hands.append(make_hand(str(i), [p], [], big_blind=0.02))
        stats = compute_stats(hands, "Hero")
        assert stats.bb_per_100 == pytest.approx(500.0)


# ---------------------------------------------------------------------------
# BB/100 All-in Adjusted
# ---------------------------------------------------------------------------

class TestBB100Adjusted:
    def test_non_allin_hand_adjusted_equals_actual(self):
        """No all-in → adjusted result is same as actual."""
        player = make_player("Hero", net_won=0.20)
        hand = make_hand("1", [player], [], big_blind=0.02)
        hand.all_in_equity = None  # no all-in equity information
        stats = compute_stats([hand], "Hero")
        assert stats.bb_per_100_adjusted == pytest.approx(stats.bb_per_100)

    def test_allin_win_with_80pct_equity(self):
        """
        All-in preflop, 200bb pot, Hero invested 100bb, 80% equity.
        PT4 adjusted = equity × pot − investment = 0.80 × 200 − 100 = +60bb.
        """
        player_win = make_player("Hero", net_won=2.00)   # won the pot
        hand = make_hand("1", [player_win], [], big_blind=0.02)
        hand.all_in_equity = {"Hero": 0.80}
        hand.all_in_pot_bb = 200.0
        hand.all_in_invested_bb = 100.0
        stats = compute_stats([hand], "Hero")
        assert stats.bb_per_100_adjusted == pytest.approx(60.0 * 100)  # per 100 hands

    def test_allin_lose_with_80pct_equity(self):
        """
        Same equity scenario but Hero runs bad and loses.
        Adjusted result is still +60bb (equity, not result).
        """
        player_lose = make_player("Hero", net_won=-2.00)  # lost the pot
        hand = make_hand("1", [player_lose], [], big_blind=0.02)
        hand.all_in_equity = {"Hero": 0.80}
        hand.all_in_pot_bb = 200.0
        hand.all_in_invested_bb = 100.0
        stats = compute_stats([hand], "Hero")
        assert stats.bb_per_100_adjusted == pytest.approx(60.0 * 100)

    def test_allin_tie_50pct_equity(self):
        """50/50 all-in in 200bb pot: adjusted = 0.50 × 200 − 100 = 0bb."""
        player = make_player("Hero", net_won=1.00)  # half the pot
        hand = make_hand("1", [player], [], big_blind=0.02)
        hand.all_in_equity = {"Hero": 0.50}
        hand.all_in_pot_bb = 200.0
        hand.all_in_invested_bb = 100.0
        stats = compute_stats([hand], "Hero")
        assert stats.bb_per_100_adjusted == pytest.approx(0.0)

    def test_adjusted_averages_over_multiple_hands(self):
        """
        Hand 1: normal hand, win 10bb.
        Hand 2: all-in, 80% equity in 200bb pot, invested 100bb → +60bb adjusted.
        Adjusted BB/100 = (10 + 60) / 2 * 100 = 3500.
        """
        p1 = make_player("Hero", net_won=0.20)   # win 10bb
        hand1 = make_hand("1", [p1], [], big_blind=0.02)
        hand1.all_in_equity = None

        p2 = make_player("Hero", net_won=-2.00)  # lost 100bb all-in
        hand2 = make_hand("2", [p2], [], big_blind=0.02)
        hand2.all_in_equity = {"Hero": 0.80}
        hand2.all_in_pot_bb = 200.0
        hand2.all_in_invested_bb = 100.0

        stats = compute_stats([hand1, hand2], "Hero")
        assert stats.bb_per_100_adjusted == pytest.approx(3500.0)

    def test_allin_deterministic_equity_not_adjusted(self):
        """
        When equity is exactly 0.0 or 1.0 the outcome is already certain —
        adjusted result must equal actual net_won (no EV substitution).
        """
        # Hero has 100% equity (e.g. opponent drawing dead) and wins
        player_win = make_player("Hero", net_won=2.00)  # won 100bb
        hand_win = make_hand("1", [player_win], [], big_blind=0.02)
        hand_win.all_in_equity = {"Hero": 1.0}
        hand_win.all_in_pot_bb = 200.0
        hand_win.all_in_invested_bb = 100.0

        stats_win = compute_stats([hand_win], "Hero")
        assert stats_win.bb_per_100_adjusted == pytest.approx(stats_win.bb_per_100)

        # Hero has 0% equity (drawing dead) and loses
        player_lose = make_player("Hero", net_won=-2.00)
        hand_lose = make_hand("2", [player_lose], [], big_blind=0.02)
        hand_lose.all_in_equity = {"Hero": 0.0}
        hand_lose.all_in_pot_bb = 200.0
        hand_lose.all_in_invested_bb = 100.0

        stats_lose = compute_stats([hand_lose], "Hero")
        assert stats_lose.bb_per_100_adjusted == pytest.approx(stats_lose.bb_per_100)

    def test_allin_equity_is_deterministic_across_runs(self):
        """
        Equity calculation must be deterministic — running compute_stats twice
        on the same all-in hand must produce identical adjusted BB/100.
        This ensures we use exact enumeration, not Monte Carlo sampling.
        """
        player = make_player("Hero", net_won=-2.00)
        hand = make_hand("1", [player], [], big_blind=0.05)
        # Known hole cards so equity can be computed
        hand.all_in_equity = {"Hero": 0.7523}   # placeholder — will be recalculated
        hand.all_in_pot_bb = 100.0
        hand.all_in_invested_bb = 50.0

        result1 = compute_stats([hand], "Hero").bb_per_100_adjusted
        result2 = compute_stats([hand], "Hero").bb_per_100_adjusted
        assert result1 == result2


# ---------------------------------------------------------------------------
# Amount Won / Dollar per 100
# ---------------------------------------------------------------------------

class TestAmountWon:
    def test_amount_won_single_hand_win(self):
        player = make_player("Hero", net_won=0.50)
        hand = make_hand("1", [player], [])
        stats = compute_stats([hand], "Hero")
        assert stats.amount_won == pytest.approx(0.50)

    def test_amount_won_single_hand_loss(self):
        player = make_player("Hero", net_won=-1.00)
        hand = make_hand("1", [player], [])
        stats = compute_stats([hand], "Hero")
        assert stats.amount_won == pytest.approx(-1.00)

    def test_amount_won_sums_across_hands(self):
        p1 = make_player("Hero", net_won=2.00)
        p2 = make_player("Hero", net_won=-0.50)
        h1 = make_hand("1", [p1], [])
        h2 = make_hand("2", [p2], [])
        stats = compute_stats([h1, h2], "Hero")
        assert stats.amount_won == pytest.approx(1.50)

    def test_amount_won_zero_when_no_hands(self):
        stats = compute_stats([], "Hero")
        assert stats.amount_won == pytest.approx(0.0)

    def test_dollar_per_100_single_win(self):
        """Win $1.00 in 1 hand → $/100 = $100.00."""
        player = make_player("Hero", net_won=1.00)
        hand = make_hand("1", [player], [])
        stats = compute_stats([hand], "Hero")
        assert stats.dollar_per_100 == pytest.approx(100.0)

    def test_dollar_per_100_scales_over_100_hands(self):
        """Win $0.10 per hand over 100 hands → $/100 = $10.00."""
        hands = [make_hand(str(i), [make_player("Hero", net_won=0.10)], []) for i in range(100)]
        stats = compute_stats(hands, "Hero")
        assert stats.dollar_per_100 == pytest.approx(10.0)

    def test_dollar_per_100_zero_when_no_hands(self):
        stats = compute_stats([], "Hero")
        assert stats.dollar_per_100 == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Saw Flop / Turn / River
# ---------------------------------------------------------------------------

def _preflop_fold(player_name: str) -> list[Action]:
    return [
        Action("SB", ActionType.POST_SB, 0.01),
        Action("BB", ActionType.POST_BB, 0.02),
        Action(player_name, ActionType.FOLD),
    ]


def _preflop_call(player_name: str) -> list[Action]:
    return [
        Action("SB", ActionType.POST_SB, 0.01),
        Action("BB", ActionType.POST_BB, 0.02),
        Action(player_name, ActionType.CALL, 0.02),
    ]


class TestSawStreets:
    def test_saw_flop_when_player_reaches_flop(self):
        player = make_player("Hero")
        preflop = Street(StreetName.PREFLOP, actions=_preflop_call("Hero"))
        flop = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        hand = make_hand_with_streets("1", [player], [preflop, flop])
        stats = compute_stats([hand], "Hero")
        assert stats.saw_flop.count == 1
        assert stats.saw_flop.total == 1

    def test_did_not_see_flop_when_folded_preflop(self):
        player = make_player("Hero")
        preflop = Street(StreetName.PREFLOP, actions=_preflop_fold("Hero"))
        hand = make_hand_with_streets("1", [player], [preflop])
        stats = compute_stats([hand], "Hero")
        assert stats.saw_flop.count == 0
        assert stats.saw_flop.total == 1

    def test_saw_flop_percentage_across_hands(self):
        player = make_player("Hero")
        preflop_call = Street(StreetName.PREFLOP, actions=_preflop_call("Hero"))
        flop = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        preflop_fold = Street(StreetName.PREFLOP, actions=_preflop_fold("Hero"))
        h1 = make_hand_with_streets("1", [player], [preflop_call, flop])
        h2 = make_hand_with_streets("2", [player], [preflop_fold])
        stats = compute_stats([h1, h2], "Hero")
        assert stats.saw_flop.count == 1
        assert stats.saw_flop.total == 2
        assert stats.saw_flop.percentage == pytest.approx(50.0)

    def test_saw_turn_when_player_reaches_turn(self):
        player = make_player("Hero")
        preflop = Street(StreetName.PREFLOP, actions=_preflop_call("Hero"))
        flop = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        turn = Street(StreetName.TURN, actions=[Action("Hero", ActionType.CHECK)])
        hand = make_hand_with_streets("1", [player], [preflop, flop, turn])
        stats = compute_stats([hand], "Hero")
        assert stats.saw_turn.count == 1
        assert stats.saw_turn.total == 1

    def test_did_not_see_turn_when_folded_on_flop(self):
        player = make_player("Hero")
        preflop = Street(StreetName.PREFLOP, actions=_preflop_call("Hero"))
        flop = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.FOLD)])
        hand = make_hand_with_streets("1", [player], [preflop, flop])
        stats = compute_stats([hand], "Hero")
        assert stats.saw_flop.count == 1
        assert stats.saw_turn.count == 0
        assert stats.saw_turn.total == 1

    def test_saw_river_when_player_reaches_river(self):
        player = make_player("Hero")
        preflop = Street(StreetName.PREFLOP, actions=_preflop_call("Hero"))
        flop = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        turn = Street(StreetName.TURN, actions=[Action("Hero", ActionType.CHECK)])
        river = Street(StreetName.RIVER, actions=[Action("Hero", ActionType.CHECK)])
        hand = make_hand_with_streets("1", [player], [preflop, flop, turn, river])
        stats = compute_stats([hand], "Hero")
        assert stats.saw_river.count == 1
        assert stats.saw_river.total == 1

    def test_did_not_see_river_when_folded_on_turn(self):
        player = make_player("Hero")
        preflop = Street(StreetName.PREFLOP, actions=_preflop_call("Hero"))
        flop = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        turn = Street(StreetName.TURN, actions=[Action("Hero", ActionType.FOLD)])
        hand = make_hand_with_streets("1", [player], [preflop, flop, turn])
        stats = compute_stats([hand], "Hero")
        assert stats.saw_turn.count == 1
        assert stats.saw_river.count == 0

    def test_all_zero_when_no_hands(self):
        stats = compute_stats([], "Hero")
        assert stats.saw_flop.count == 0
        assert stats.saw_flop.total == 0
        assert stats.saw_turn.count == 0
        assert stats.saw_river.count == 0

    def test_saw_flop_gte_saw_turn_gte_saw_river(self):
        """Ordering invariant: flop ≥ turn ≥ river in count."""
        player = make_player("Hero")
        # hand 1: reaches river
        p1 = Street(StreetName.PREFLOP, actions=_preflop_call("Hero"))
        f1 = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        t1 = Street(StreetName.TURN, actions=[Action("Hero", ActionType.CHECK)])
        r1 = Street(StreetName.RIVER, actions=[Action("Hero", ActionType.CHECK)])
        h1 = make_hand_with_streets("1", [player], [p1, f1, t1, r1])
        # hand 2: folds on flop
        p2 = Street(StreetName.PREFLOP, actions=_preflop_call("Hero"))
        f2 = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.FOLD)])
        h2 = make_hand_with_streets("2", [player], [p2, f2])
        # hand 3: folds preflop
        p3 = Street(StreetName.PREFLOP, actions=_preflop_fold("Hero"))
        h3 = make_hand_with_streets("3", [player], [p3])
        stats = compute_stats([h1, h2, h3], "Hero")
        assert stats.saw_flop.count >= stats.saw_turn.count >= stats.saw_river.count


# ---------------------------------------------------------------------------
# S-effort metric helpers
# ---------------------------------------------------------------------------

def make_player_pos(name: str, seat: int, position: Position, net_won: float = 0.0) -> Player:
    p = Player(name=name, seat=seat, stack=2.00, net_won=net_won)
    p.position = position
    return p


def make_preflop_hand(hand_id: str, players: list[Player], actions: list[Action], big_blind: float = 0.02) -> Hand:
    preflop = Street(StreetName.PREFLOP, actions=actions)
    return Hand(
        hand_id=hand_id,
        game_type=GameType.NLHE,
        small_blind=big_blind / 2,
        big_blind=big_blind,
        table_name="T",
        played_at=datetime(2024, 1, 1),
        players=players,
        streets=[preflop],
    )


# ---------------------------------------------------------------------------
# RFI (Raise First In)
# ---------------------------------------------------------------------------

class TestRFI:
    def test_open_raise_from_co_is_rfi(self):
        hero = make_player_pos("Hero", 3, Position.CO)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.FOLD),
            Action("Hero", ActionType.RAISE, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.rfi.count == 1
        assert stats.rfi.total == 1

    def test_calling_is_not_rfi(self):
        hero = make_player_pos("Hero", 3, Position.CO)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.CALL, 0.02),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.rfi.count == 0
        assert stats.rfi.total == 1

    def test_3bet_is_not_rfi(self):
        """Raising after someone already raised is a 3bet, not RFI."""
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.RAISE, 0.18),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.rfi.count == 0
        assert stats.rfi.total == 0  # no RFI opportunity (pot was not clean)

    def test_rfi_opportunity_lost_to_limper(self):
        """Limper before hero kills RFI opportunity."""
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.CALL, 0.02),  # limp
            Action("Hero", ActionType.RAISE, 0.08),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.rfi.count == 0
        assert stats.rfi.total == 0

    def test_fold_preflop_no_rfi_opportunity_if_raiser_before(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.rfi.total == 0

    def test_rfi_count_and_total_across_multiple_hands(self):
        hero = make_player_pos("Hero", 3, Position.CO)
        h1 = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
        ])
        h2 = make_preflop_hand("2", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([h1, h2], "Hero")
        assert stats.rfi.count == 1
        assert stats.rfi.total == 2


# ---------------------------------------------------------------------------
# Limp
# ---------------------------------------------------------------------------

class TestLimp:
    def test_calling_bb_as_first_in_is_limp(self):
        hero = make_player_pos("Hero", 3, Position.CO)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.CALL, 0.02),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.limp.count == 1
        assert stats.limp.total == 1

    def test_raise_is_not_limp(self):
        hero = make_player_pos("Hero", 3, Position.CO)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.limp.count == 0
        assert stats.limp.total == 1

    def test_calling_after_raiser_is_not_limp(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.CALL, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.limp.count == 0
        assert stats.limp.total == 0  # no limp opportunity


# ---------------------------------------------------------------------------
# Call Open Raise
# ---------------------------------------------------------------------------

class TestCallOpenRaise:
    def test_calling_a_raiser_counts(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.CALL, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.call_open.count == 1
        assert stats.call_open.total == 1

    def test_folding_to_raiser_counts_in_denominator(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.call_open.count == 0
        assert stats.call_open.total == 1

    def test_3betting_is_not_call_open(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.RAISE, 0.18),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.call_open.count == 0
        assert stats.call_open.total == 1

    def test_no_opportunity_when_no_raiser(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.call_open.total == 0


# ---------------------------------------------------------------------------
# 3Bet
# ---------------------------------------------------------------------------

class TestThreeBet:
    def test_re_raise_after_open_is_3bet(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.RAISE, 0.18),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.three_bet.count == 1
        assert stats.three_bet.total == 1

    def test_call_after_open_is_not_3bet(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.CALL, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.three_bet.count == 0
        assert stats.three_bet.total == 1

    def test_no_opportunity_when_no_open(self):
        hero = make_player_pos("Hero", 3, Position.CO)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.three_bet.total == 0


# ---------------------------------------------------------------------------
# 4Bet
# ---------------------------------------------------------------------------

class TestFourBet:
    def test_re_raise_after_3bet_is_4bet(self):
        hero = make_player_pos("Hero", 1, Position.UTG)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),   # open
            Action("BTN", ActionType.RAISE, 0.18),    # 3bet
            Action("Hero", ActionType.RAISE, 0.50),   # 4bet
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.four_bet.count == 1
        assert stats.four_bet.total == 1

    def test_fold_to_3bet_is_in_4bet_denominator(self):
        hero = make_player_pos("Hero", 1, Position.UTG)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
            Action("BTN", ActionType.RAISE, 0.18),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.four_bet.count == 0
        assert stats.four_bet.total == 1

    def test_no_opportunity_when_no_3bet_against_hero(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.RAISE, 0.18),   # hero 3bets; no one re-raises
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.four_bet.total == 0


# ---------------------------------------------------------------------------
# Fold to 3Bet
# ---------------------------------------------------------------------------

class TestFoldToThreeBet:
    def test_fold_to_3bet_after_open(self):
        hero = make_player_pos("Hero", 1, Position.UTG)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
            Action("BTN", ActionType.RAISE, 0.18),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_to_3bet.count == 1
        assert stats.fold_to_3bet.total == 1

    def test_call_3bet_is_not_fold(self):
        hero = make_player_pos("Hero", 1, Position.UTG)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
            Action("BTN", ActionType.RAISE, 0.18),
            Action("Hero", ActionType.CALL, 0.18),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_to_3bet.count == 0
        assert stats.fold_to_3bet.total == 1

    def test_4bet_not_fold_to_3bet(self):
        hero = make_player_pos("Hero", 1, Position.UTG)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
            Action("BTN", ActionType.RAISE, 0.18),
            Action("Hero", ActionType.RAISE, 0.50),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_to_3bet.count == 0
        assert stats.fold_to_3bet.total == 1

    def test_no_opportunity_when_not_open_raiser(self):
        """Player who didn't open raise has no fold_to_3bet opportunity."""
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_to_3bet.total == 0


# ---------------------------------------------------------------------------
# Call 3Bet
# ---------------------------------------------------------------------------

class TestCallThreeBet:
    def test_call_after_3bet(self):
        hero = make_player_pos("Hero", 1, Position.UTG)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
            Action("BTN", ActionType.RAISE, 0.18),
            Action("Hero", ActionType.CALL, 0.18),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.call_3bet.count == 1
        assert stats.call_3bet.total == 1

    def test_fold_is_not_call_3bet(self):
        hero = make_player_pos("Hero", 1, Position.UTG)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
            Action("BTN", ActionType.RAISE, 0.18),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.call_3bet.count == 0
        assert stats.call_3bet.total == 1


# ---------------------------------------------------------------------------
# Fold to 4Bet
# ---------------------------------------------------------------------------

class TestFoldToFourBet:
    def test_fold_to_4bet_after_3betting(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.RAISE, 0.18),   # 3bet
            Action("UTG", ActionType.RAISE, 0.50),    # 4bet
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_to_4bet.count == 1
        assert stats.fold_to_4bet.total == 1

    def test_5bet_is_not_fold_to_4bet(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.RAISE, 0.18),
            Action("UTG", ActionType.RAISE, 0.50),
            Action("Hero", ActionType.RAISE, 1.50),   # 5bet shove
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_to_4bet.count == 0
        assert stats.fold_to_4bet.total == 1

    def test_no_fold_to_4bet_opportunity_if_hero_didnt_3bet(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_to_4bet.total == 0


# ---------------------------------------------------------------------------
# Attempt to Steal
# ---------------------------------------------------------------------------

class TestAttemptSteal:
    def test_open_raise_from_btn_is_steal(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.FOLD),
            Action("Hero", ActionType.RAISE, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.attempt_steal.count == 1
        assert stats.attempt_steal.total == 1

    def test_open_raise_from_co_is_steal(self):
        hero = make_player_pos("Hero", 3, Position.CO)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.attempt_steal.count == 1

    def test_open_raise_from_sb_is_steal(self):
        hero = make_player_pos("Hero", 1, Position.SB)
        hand = make_preflop_hand("1", [hero], [
            Action("Hero", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.attempt_steal.count == 1

    def test_open_raise_from_utg_is_not_steal(self):
        hero = make_player_pos("Hero", 1, Position.UTG)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.attempt_steal.count == 0
        assert stats.attempt_steal.total == 0  # no steal opportunity from UTG

    def test_limp_is_not_steal(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.CALL, 0.02),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.attempt_steal.count == 0
        assert stats.attempt_steal.total == 1

    def test_no_steal_opportunity_with_limper_before(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.CALL, 0.02),   # limper
            Action("Hero", ActionType.RAISE, 0.08),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.attempt_steal.total == 0


# ---------------------------------------------------------------------------
# Fold BB to Steal
# ---------------------------------------------------------------------------

class TestFoldBBToSteal:
    def test_fold_bb_to_btn_steal(self):
        hero = make_player_pos("Hero", 2, Position.BB)
        btn = make_player_pos("BTN", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero, btn], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("Hero", ActionType.POST_BB, 0.02),
            Action("BTN", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_bb_to_steal.count == 1
        assert stats.fold_bb_to_steal.total == 1

    def test_call_bb_vs_steal_is_not_fold(self):
        hero = make_player_pos("Hero", 2, Position.BB)
        btn = make_player_pos("BTN", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero, btn], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("Hero", ActionType.POST_BB, 0.02),
            Action("BTN", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.CALL, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_bb_to_steal.count == 0
        assert stats.fold_bb_to_steal.total == 1

    def test_no_steal_opportunity_when_raiser_not_in_steal_position(self):
        """UTG open vs BB — not a steal, no fold_bb_to_steal opportunity."""
        hero = make_player_pos("Hero", 2, Position.BB)
        utg = make_player_pos("UTG", 1, Position.UTG)
        hand = make_preflop_hand("1", [hero, utg], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("Hero", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_bb_to_steal.total == 0

    def test_no_fold_bb_to_steal_when_hero_not_bb(self):
        hero = make_player_pos("Hero", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero], [
            Action("SB", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_bb_to_steal.total == 0


# ---------------------------------------------------------------------------
# Fold SB to Steal
# ---------------------------------------------------------------------------

class TestFoldSBToSteal:
    def test_fold_sb_to_btn_steal(self):
        hero = make_player_pos("Hero", 1, Position.SB)
        btn = make_player_pos("BTN", 4, Position.BTN)
        hand = make_preflop_hand("1", [hero, btn], [
            Action("Hero", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("BTN", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_sb_to_steal.count == 1
        assert stats.fold_sb_to_steal.total == 1

    def test_fold_sb_to_co_steal(self):
        hero = make_player_pos("Hero", 1, Position.SB)
        co = make_player_pos("CO", 3, Position.CO)
        hand = make_preflop_hand("1", [hero, co], [
            Action("Hero", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("CO", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_sb_to_steal.count == 1

    def test_sb_steal_attempt_not_a_fold_sb_to_steal_opportunity(self):
        """SB raising is a steal, not an opportunity to fold to steal."""
        hero = make_player_pos("Hero", 1, Position.SB)
        hand = make_preflop_hand("1", [hero], [
            Action("Hero", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("Hero", ActionType.RAISE, 0.06),
        ])
        stats = compute_stats([hand], "Hero")
        assert stats.fold_sb_to_steal.total == 0

    def test_sb_raise_from_sb_not_a_fold_sb_opportunity(self):
        """SB can't steal from SB position."""
        hero = make_player_pos("Hero", 1, Position.SB)
        sb2 = make_player_pos("SB2", 2, Position.SB)
        # SB raising — but this is the hero's own position, no opportunity
        hand = make_preflop_hand("1", [hero], [
            Action("Hero", ActionType.POST_SB, 0.01),
            Action("BB", ActionType.POST_BB, 0.02),
            Action("UTG", ActionType.RAISE, 0.06),
            Action("Hero", ActionType.FOLD),
        ])
        stats = compute_stats([hand], "Hero")
        # UTG is not a steal position
        assert stats.fold_sb_to_steal.total == 0


# ---------------------------------------------------------------------------
# WTSD (Went to Showdown)
# ---------------------------------------------------------------------------

class TestWTSD:
    def test_showing_cards_is_wtsd(self):
        hero = make_player_pos("Hero", 1, Position.UTG, net_won=1.0)
        preflop = Street(StreetName.PREFLOP, actions=[
            Action("SB", ActionType.POST_SB),
            Action("BB", ActionType.POST_BB),
            Action("Hero", ActionType.CALL, 0.02),
        ])
        flop = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        river = Street(StreetName.RIVER, actions=[
            Action("Hero", ActionType.CHECK),
            Action("Villain", ActionType.CHECK),
            Action("Hero", ActionType.SHOWS),
        ])
        hand = make_hand_with_streets("1", [hero], [preflop, flop, river])
        stats = compute_stats([hand], "Hero")
        assert stats.wtsd.count == 1

    def test_muck_is_wtsd(self):
        hero = make_player_pos("Hero", 1, Position.UTG, net_won=0.0)
        preflop = Street(StreetName.PREFLOP, actions=[Action("Hero", ActionType.CALL, 0.02)])
        flop = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        river = Street(StreetName.RIVER, actions=[Action("Hero", ActionType.MUCKS)])
        hand = make_hand_with_streets("1", [hero], [preflop, flop, river])
        stats = compute_stats([hand], "Hero")
        assert stats.wtsd.count == 1

    def test_fold_on_river_is_not_wtsd(self):
        hero = make_player_pos("Hero", 1, Position.UTG)
        preflop = Street(StreetName.PREFLOP, actions=[Action("Hero", ActionType.CALL, 0.02)])
        flop = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        river = Street(StreetName.RIVER, actions=[Action("Hero", ActionType.FOLD)])
        hand = make_hand_with_streets("1", [hero], [preflop, flop, river])
        stats = compute_stats([hand], "Hero")
        assert stats.wtsd.count == 0

    def test_wtsd_denominator_is_saw_flop(self):
        """WTSD denominator = hands player saw flop."""
        hero = make_player_pos("Hero", 1, Position.UTG, net_won=1.0)
        # hand 1: saw flop and went to showdown
        p1 = Street(StreetName.PREFLOP, actions=[Action("Hero", ActionType.CALL, 0.02)])
        f1 = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        r1 = Street(StreetName.RIVER, actions=[Action("Hero", ActionType.SHOWS)])
        h1 = make_hand_with_streets("1", [hero], [p1, f1, r1])
        # hand 2: saw flop but folded on turn (no showdown)
        p2 = Street(StreetName.PREFLOP, actions=[Action("Hero", ActionType.CALL, 0.02)])
        f2 = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        t2 = Street(StreetName.TURN, actions=[Action("Hero", ActionType.FOLD)])
        h2 = make_hand_with_streets("2", [hero], [p2, f2, t2])
        # hand 3: folded preflop (not in denominator)
        p3 = Street(StreetName.PREFLOP, actions=[Action("Hero", ActionType.FOLD)])
        h3 = make_hand_with_streets("3", [hero], [p3])
        stats = compute_stats([h1, h2, h3], "Hero")
        assert stats.wtsd.count == 1
        assert stats.wtsd.total == 2  # saw flop in h1 and h2


# ---------------------------------------------------------------------------
# W$SD (Won $ at Showdown)
# ---------------------------------------------------------------------------

class TestWSD:
    def test_win_at_showdown(self):
        hero = make_player_pos("Hero", 1, Position.UTG, net_won=1.0)
        preflop = Street(StreetName.PREFLOP, actions=[Action("Hero", ActionType.CALL, 0.02)])
        flop = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        river = Street(StreetName.RIVER, actions=[Action("Hero", ActionType.SHOWS)])
        hand = make_hand_with_streets("1", [hero], [preflop, flop, river])
        stats = compute_stats([hand], "Hero")
        assert stats.wsd.count == 1
        assert stats.wsd.total == 1

    def test_lose_at_showdown(self):
        hero = make_player_pos("Hero", 1, Position.UTG, net_won=-0.50)
        preflop = Street(StreetName.PREFLOP, actions=[Action("Hero", ActionType.CALL, 0.02)])
        flop = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        river = Street(StreetName.RIVER, actions=[Action("Hero", ActionType.MUCKS)])
        hand = make_hand_with_streets("1", [hero], [preflop, flop, river])
        stats = compute_stats([hand], "Hero")
        assert stats.wsd.count == 0
        assert stats.wsd.total == 1

    def test_wsd_denominator_is_wtsd(self):
        hero_win = make_player_pos("Hero", 1, Position.UTG, net_won=1.0)
        hero_lose = make_player_pos("Hero", 1, Position.UTG, net_won=-0.50)
        preflop_s = Street(StreetName.PREFLOP, actions=[Action("Hero", ActionType.CALL, 0.02)])
        flop_s = Street(StreetName.FLOP, actions=[Action("Hero", ActionType.CHECK)])
        river_win = Street(StreetName.RIVER, actions=[Action("Hero", ActionType.SHOWS)])
        river_lose = Street(StreetName.RIVER, actions=[Action("Hero", ActionType.MUCKS)])
        h1 = make_hand_with_streets("1", [hero_win], [preflop_s, flop_s, river_win])
        h2 = make_hand_with_streets("2", [hero_lose], [preflop_s, flop_s, river_lose])
        stats = compute_stats([h1, h2], "Hero")
        assert stats.wsd.total == 2
        assert stats.wsd.count == 1
        assert stats.wsd.percentage == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Std Deviation
# ---------------------------------------------------------------------------

class TestStdDev:
    def test_single_hand_std_dev_is_zero(self):
        p = make_player("Hero", net_won=0.20)
        hand = make_hand("1", [p], [], big_blind=0.02)
        stats = compute_stats([hand], "Hero")
        assert stats.std_dev == pytest.approx(0.0)

    def test_two_symmetric_hands(self):
        """Win 5bb then lose 5bb: mean=0, each deviation=5, std_dev=5."""
        p1 = make_player("Hero", net_won=0.10)  # +5bb
        p2 = make_player("Hero", net_won=-0.10)  # -5bb
        h1 = make_hand("1", [p1], [], big_blind=0.02)
        h2 = make_hand("2", [p2], [], big_blind=0.02)
        stats = compute_stats([h1, h2], "Hero")
        assert stats.std_dev == pytest.approx(5.0)

    def test_identical_hands_std_dev_is_zero(self):
        hands = [make_hand(str(i), [make_player("Hero", net_won=0.10)], [], big_blind=0.02) for i in range(10)]
        stats = compute_stats(hands, "Hero")
        assert stats.std_dev == pytest.approx(0.0)

    def test_zero_hands_std_dev_is_zero(self):
        stats = compute_stats([], "Hero")
        assert stats.std_dev == pytest.approx(0.0)
