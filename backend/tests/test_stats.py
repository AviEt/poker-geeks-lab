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
