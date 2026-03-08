"""
Poker stat computations.

All functions operate on pure domain objects (Hand, Player) — no DB, no I/O.

Stat definitions follow PokerTracker4 / Hold'em Manager conventions:
  VPIP  = voluntary preflop entries / hands_dealt
  PFR   = preflop raises / hands_dealt
  BB/100 = net_bb_won / hands * 100
  BB/100 all-in adjusted = equity-adjusted net_bb_won / hands * 100

"hands_dealt" excludes walk hands where Hero is the BB — PT4 definition.
In those hands Hero had no opportunity to voluntarily act.
Other walk hands (Hero folded as non-BB) still count in the denominator.
"""

from dataclasses import dataclass

from domain.action import ActionType
from domain.hand import Hand
from domain.street import StreetName


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class StatLine:
    """A countable stat expressed as a fraction and percentage."""
    count: int
    total: int

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return self.count / self.total * 100


@dataclass
class PlayerStats:
    vpip: StatLine
    pfr: StatLine
    bb_per_100: float
    bb_per_100_adjusted: float
    hands: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VOLUNTARY_ACTIONS = {ActionType.CALL, ActionType.RAISE, ActionType.BET}
_BLIND_POSTS = {ActionType.POST_SB, ActionType.POST_BB, ActionType.POST_ANTE}
_RAISE_ACTIONS = {ActionType.RAISE}


def _preflop_actions_for(hand: Hand, player_name: str) -> list:
    preflop = next(
        (s for s in hand.streets if s.name == StreetName.PREFLOP), None
    )
    if not preflop:
        return []
    return [a for a in preflop.actions if a.player_name == player_name]


def _is_blind_poster(hand: Hand, player_name: str) -> bool:
    preflop = next(
        (s for s in hand.streets if s.name == StreetName.PREFLOP), None
    )
    if not preflop:
        return False
    return any(
        a.player_name == player_name and a.action_type in _BLIND_POSTS
        for a in preflop.actions
    )


def _player_in_hand(hand: Hand, player_name: str) -> bool:
    return any(p.name == player_name for p in hand.players)


def _is_bb_in_walk(hand: Hand, player_name: str) -> bool:
    """True when player_name is the BB in a walk hand (PT4: exclude from denominator)."""
    if not hand.is_walk:
        return False
    preflop = next((s for s in hand.streets if s.name == StreetName.PREFLOP), None)
    if not preflop:
        return False
    return any(
        a.player_name == player_name and a.action_type == ActionType.POST_BB
        for a in preflop.actions
    )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_stats(hands: list[Hand], player_name: str) -> PlayerStats:
    vpip_count = 0
    vpip_total = 0
    pfr_count = 0
    pfr_total = 0
    net_bb_won = 0.0
    net_bb_won_adjusted = 0.0
    total_hands = 0

    for hand in hands:
        if not _player_in_hand(hand, player_name):
            continue

        total_hands += 1
        big_blind = hand.big_blind

        # BB/100: net chips won converted to big blinds
        player = next(p for p in hand.players if p.name == player_name)
        net_bb_won += player.net_won / big_blind

        # BB/100 all-in adjusted
        # For all-in pots with cards remaining: replace actual result with equity × pot.
        # Formula source: PokerTracker4 / Hold'em Manager definition.
        if hand.all_in_equity and player_name in hand.all_in_equity and hand.all_in_pot_bb is not None:
            equity = hand.all_in_equity[player_name]
            net_bb_won_adjusted += equity * hand.all_in_pot_bb
        else:
            net_bb_won_adjusted += player.net_won / big_blind

        # VPIP / PFR denominator: PT4 excludes only walks where Hero is the BB.
        # In those hands Hero had no voluntary decision. Walks where Hero is a
        # non-BB (folded preflop normally) still count in the denominator.
        if _is_bb_in_walk(hand, player_name):
            continue

        vpip_total += 1
        pfr_total += 1

        if hand.is_walk:
            continue

        actions = _preflop_actions_for(hand, player_name)
        posted_blind = _is_blind_poster(hand, player_name)

        # VPIP: voluntary entry = call/raise by any player, OR call/raise by blind poster
        # Checking BB option or folding from blind = not VPIP
        for action in actions:
            if action.action_type in _VOLUNTARY_ACTIONS:
                # If BB posts and then calls/raises their own BB, that's voluntary
                # A CHECK from a blind poster is not voluntary
                vpip_count += 1
                break

        # PFR: any raise preflop
        for action in actions:
            if action.action_type in _RAISE_ACTIONS:
                pfr_count += 1
                break

    bb_per_100 = (net_bb_won / total_hands * 100) if total_hands else 0.0
    bb_per_100_adj = (net_bb_won_adjusted / total_hands * 100) if total_hands else 0.0

    return PlayerStats(
        vpip=StatLine(count=vpip_count, total=vpip_total),
        pfr=StatLine(count=pfr_count, total=pfr_total),
        bb_per_100=bb_per_100,
        bb_per_100_adjusted=bb_per_100_adj,
        hands=total_hands,
    )
