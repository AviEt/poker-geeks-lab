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

import math
from dataclasses import dataclass

from domain.action import ActionType
from domain.hand import Hand
from domain.player import Position
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
    amount_won: float = 0.0
    dollar_per_100: float = 0.0
    saw_flop: StatLine = None
    saw_turn: StatLine = None
    saw_river: StatLine = None
    rfi: StatLine = None
    limp: StatLine = None
    call_open: StatLine = None
    three_bet: StatLine = None
    four_bet: StatLine = None
    fold_to_3bet: StatLine = None
    fold_to_4bet: StatLine = None
    call_3bet: StatLine = None
    attempt_steal: StatLine = None
    fold_bb_to_steal: StatLine = None
    fold_sb_to_steal: StatLine = None
    wtsd: StatLine = None
    wsd: StatLine = None
    std_dev: float = 0.0

    def __post_init__(self):
        _fields = [
            'saw_flop', 'saw_turn', 'saw_river',
            'rfi', 'limp', 'call_open',
            'three_bet', 'four_bet',
            'fold_to_3bet', 'fold_to_4bet', 'call_3bet',
            'attempt_steal', 'fold_bb_to_steal', 'fold_sb_to_steal',
            'wtsd', 'wsd',
        ]
        for f in _fields:
            if getattr(self, f) is None:
                setattr(self, f, StatLine(0, 0))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VOLUNTARY_ACTIONS = {ActionType.CALL, ActionType.RAISE, ActionType.BET}
_BLIND_POSTS = {ActionType.POST_SB, ActionType.POST_BB, ActionType.POST_ANTE}
_RAISE_ACTIONS = {ActionType.RAISE}
_STEAL_POSITIONS = {Position.CO, Position.BTN, Position.SB}
_SHOWDOWN_ACTIONS = {ActionType.SHOWS, ActionType.MUCKS}


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


def _player_folded_in_street(hand: Hand, player_name: str, street_name: StreetName) -> bool:
    street = next((s for s in hand.streets if s.name == street_name), None)
    if not street:
        return False
    return any(
        a.player_name == player_name and a.action_type == ActionType.FOLD
        for a in street.actions
    )


def _hand_has_street(hand: Hand, street_name: StreetName) -> bool:
    return any(s.name == street_name for s in hand.streets)


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


def _analyze_preflop(hand: Hand, player_name: str) -> dict:
    """
    Analyze the preflop action sequence from player_name's perspective.
    Returns a dict of booleans representing situations the player was in.

    raise_level = number of raises that had occurred BEFORE player acted.
    - 0 = clean pot (RFI / limp opportunity)
    - 1 = one raise before player (3bet / call open opportunity)
    - 2 = two raises before player (4bet opportunity)

    Multiple actions per player are tracked (e.g. open-raise then face 3bet).
    """
    preflop = next((s for s in hand.streets if s.name == StreetName.PREFLOP), None)
    _zero = dict(
        rfi_opportunity=False, rfi_made=False,
        limp_opportunity=False, limp_made=False,
        call_open_opportunity=False, called_open=False, three_bet_made=False,
        four_bet_opportunity=False, four_bet_made=False,
        fold_to_3bet_opportunity=False, fold_to_3bet=False,
        call_3bet_made=False,
        fold_to_4bet_opportunity=False, fold_to_4bet=False,
        steal_opportunity=False, steal_made=False,
        faced_steal_as_bb=False, fold_bb_to_steal=False,
        faced_steal_as_sb=False, fold_sb_to_steal=False,
    )
    if not preflop:
        return _zero

    player_obj = next((p for p in hand.players if p.name == player_name), None)
    if not player_obj:
        return _zero
    player_pos = player_obj.position

    raise_count = 0   # raises so far
    call_count = 0    # calls (limps) so far
    first_raiser_pos = None

    # Each element: (raise_level, call_level, action_type, first_raiser_pos_at_time)
    player_occurrences: list[tuple[int, int, ActionType, Position | None]] = []

    for action in preflop.actions:
        if action.action_type in _BLIND_POSTS:
            continue
        if action.player_name == player_name:
            player_occurrences.append((raise_count, call_count, action.action_type, first_raiser_pos))
        if action.action_type == ActionType.RAISE:
            if first_raiser_pos is None:
                raiser_obj = next((p for p in hand.players if p.name == action.player_name), None)
                if raiser_obj:
                    first_raiser_pos = raiser_obj.position
            raise_count += 1
        elif action.action_type == ActionType.CALL:
            call_count += 1

    if not player_occurrences:
        return _zero

    result = dict(_zero)
    first_rl, first_cl, first_act, first_raiser_p = player_occurrences[0]

    # --- RFI / Limp ---
    if first_rl == 0 and first_cl == 0:
        result['rfi_opportunity'] = True
        result['limp_opportunity'] = True
        if first_act == ActionType.RAISE:
            result['rfi_made'] = True
        elif first_act == ActionType.CALL:
            result['limp_made'] = True

    # --- Call open / 3Bet ---
    if first_rl == 1 and first_cl == 0:
        result['call_open_opportunity'] = True
        if first_act == ActionType.CALL:
            result['called_open'] = True
        elif first_act == ActionType.RAISE:
            result['three_bet_made'] = True

    # --- 4Bet (player faces 2 raises as first action) ---
    if first_rl == 2:
        result['four_bet_opportunity'] = True
        if first_act == ActionType.RAISE:
            result['four_bet_made'] = True

    # --- Fold/Call to 3Bet (player open-raised, then faces 3bet) ---
    if first_rl == 0 and first_act == ActionType.RAISE:
        for rl, cl, act, _ in player_occurrences[1:]:
            if rl == 2:  # two raises before player's second action = someone 3bet
                result['fold_to_3bet_opportunity'] = True
                result['four_bet_opportunity'] = True
                if act == ActionType.FOLD:
                    result['fold_to_3bet'] = True
                elif act == ActionType.CALL:
                    result['call_3bet_made'] = True
                elif act == ActionType.RAISE:
                    result['four_bet_made'] = True
                break

    # --- Fold to 4Bet (player 3-bet, then faces 4bet) ---
    three_bet_idx = next(
        (i for i, (rl, cl, act, _) in enumerate(player_occurrences) if rl == 1 and act == ActionType.RAISE),
        None,
    )
    if three_bet_idx is not None:
        for rl, cl, act, _ in player_occurrences[three_bet_idx + 1:]:
            if rl == 3:
                result['fold_to_4bet_opportunity'] = True
                if act == ActionType.FOLD:
                    result['fold_to_4bet'] = True
                break

    # --- Steal (CO/BTN/SB, clean pot) ---
    if player_pos in _STEAL_POSITIONS and first_rl == 0 and first_cl == 0:
        result['steal_opportunity'] = True
        if first_act == ActionType.RAISE:
            result['steal_made'] = True

    # --- Fold BB to Steal ---
    if player_pos == Position.BB and first_rl == 1 and first_cl == 0:
        if first_raiser_p in _STEAL_POSITIONS:
            result['faced_steal_as_bb'] = True
            if first_act == ActionType.FOLD:
                result['fold_bb_to_steal'] = True

    # --- Fold SB to Steal (only CO/BTN qualify as stealer against SB) ---
    if player_pos == Position.SB and first_rl == 1 and first_cl == 0:
        if first_raiser_p in {Position.CO, Position.BTN}:
            result['faced_steal_as_sb'] = True
            if first_act == ActionType.FOLD:
                result['fold_sb_to_steal'] = True

    return result


def _went_to_showdown(hand: Hand, player_name: str) -> bool:
    """Player reached showdown (showed or mucked cards)."""
    return any(
        a.player_name == player_name and a.action_type in _SHOWDOWN_ACTIONS
        for s in hand.streets
        for a in s.actions
    )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_stats(hands: list[Hand], player_name: str) -> PlayerStats:  # noqa: C901
    vpip_count = 0
    vpip_total = 0
    pfr_count = 0
    pfr_total = 0
    net_bb_won = 0.0
    net_bb_won_adjusted = 0.0
    total_hands = 0
    amount_won = 0.0
    bb_per_hand: list[float] = []

    saw_flop_count = 0
    saw_turn_count = 0
    saw_river_count = 0

    rfi_count = 0;       rfi_total = 0
    limp_count = 0;      limp_total = 0
    call_open_count = 0; call_open_total = 0
    three_bet_count = 0; three_bet_total = 0
    four_bet_count = 0;  four_bet_total = 0
    fold_3bet_count = 0; fold_3bet_total = 0
    fold_4bet_count = 0; fold_4bet_total = 0
    call_3bet_count = 0; call_3bet_total = 0
    steal_count = 0;     steal_total = 0
    fold_bb_steal_count = 0; fold_bb_steal_total = 0
    fold_sb_steal_count = 0; fold_sb_steal_total = 0
    wtsd_count = 0;      wtsd_total = 0
    wsd_count = 0;       wsd_total = 0

    for hand in hands:
        if not _player_in_hand(hand, player_name):
            continue

        total_hands += 1
        big_blind = hand.big_blind

        # BB/100: net chips won converted to big blinds
        player = next(p for p in hand.players if p.name == player_name)
        bb_this_hand = player.net_won / big_blind
        net_bb_won += bb_this_hand
        bb_per_hand.append(bb_this_hand)
        amount_won += player.net_won

        # Saw flop/turn/river
        folded_preflop = _player_folded_in_street(hand, player_name, StreetName.PREFLOP)
        saw_flop = _hand_has_street(hand, StreetName.FLOP) and not folded_preflop
        if saw_flop:
            saw_flop_count += 1
            folded_flop = _player_folded_in_street(hand, player_name, StreetName.FLOP)
            saw_turn = _hand_has_street(hand, StreetName.TURN) and not folded_flop
            if saw_turn:
                saw_turn_count += 1
                folded_turn = _player_folded_in_street(hand, player_name, StreetName.TURN)
                if _hand_has_street(hand, StreetName.RIVER) and not folded_turn:
                    saw_river_count += 1

        # BB/100 all-in adjusted
        if (hand.all_in_equity and player_name in hand.all_in_equity
                and hand.all_in_pot_bb is not None and hand.all_in_invested_bb is not None):
            equity = hand.all_in_equity[player_name]
            rake_bb = hand.rake / big_blind
            net_bb_won_adjusted += equity * (hand.all_in_pot_bb - rake_bb) - hand.all_in_invested_bb
        else:
            net_bb_won_adjusted += bb_this_hand

        # WTSD / W$SD (denominator: saw_flop)
        if saw_flop:
            wtsd_total += 1
            if _went_to_showdown(hand, player_name):
                wtsd_count += 1
                wsd_total += 1
                if player.net_won > 0:
                    wsd_count += 1

        # VPIP / PFR denominator
        if _is_bb_in_walk(hand, player_name):
            continue
        vpip_total += 1
        pfr_total += 1

        if hand.is_walk:
            continue

        actions = _preflop_actions_for(hand, player_name)
        posted_blind = _is_blind_poster(hand, player_name)

        # VPIP
        for action in actions:
            if action.action_type in _VOLUNTARY_ACTIONS:
                vpip_count += 1
                break

        # PFR
        for action in actions:
            if action.action_type in _RAISE_ACTIONS:
                pfr_count += 1
                break

        # Preflop situation analysis
        pf = _analyze_preflop(hand, player_name)

        if pf['rfi_opportunity']:     rfi_total += 1
        if pf['rfi_made']:            rfi_count += 1
        if pf['limp_opportunity']:    limp_total += 1
        if pf['limp_made']:           limp_count += 1
        if pf['call_open_opportunity']:   call_open_total += 1
        if pf['called_open']:             call_open_count += 1
        if pf['call_open_opportunity']:   three_bet_total += 1
        if pf['three_bet_made']:          three_bet_count += 1
        if pf['four_bet_opportunity']:    four_bet_total += 1
        if pf['four_bet_made']:           four_bet_count += 1
        if pf['fold_to_3bet_opportunity']: fold_3bet_total += 1
        if pf['fold_to_3bet']:             fold_3bet_count += 1
        if pf['fold_to_3bet_opportunity']: call_3bet_total += 1
        if pf['call_3bet_made']:           call_3bet_count += 1
        if pf['fold_to_4bet_opportunity']: fold_4bet_total += 1
        if pf['fold_to_4bet']:             fold_4bet_count += 1
        if pf['steal_opportunity']:    steal_total += 1
        if pf['steal_made']:           steal_count += 1
        if pf['faced_steal_as_bb']:    fold_bb_steal_total += 1
        if pf['fold_bb_to_steal']:     fold_bb_steal_count += 1
        if pf['faced_steal_as_sb']:    fold_sb_steal_total += 1
        if pf['fold_sb_to_steal']:     fold_sb_steal_count += 1

    bb_per_100 = (net_bb_won / total_hands * 100) if total_hands else 0.0
    bb_per_100_adj = (net_bb_won_adjusted / total_hands * 100) if total_hands else 0.0
    dollar_per_100 = (amount_won / total_hands * 100) if total_hands else 0.0

    # Standard deviation of BB won per hand (population std dev, PT4 convention)
    if len(bb_per_hand) >= 2:
        mean = net_bb_won / total_hands
        variance = sum((x - mean) ** 2 for x in bb_per_hand) / len(bb_per_hand)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0

    return PlayerStats(
        vpip=StatLine(count=vpip_count, total=vpip_total),
        pfr=StatLine(count=pfr_count, total=pfr_total),
        bb_per_100=bb_per_100,
        bb_per_100_adjusted=bb_per_100_adj,
        hands=total_hands,
        amount_won=amount_won,
        dollar_per_100=dollar_per_100,
        saw_flop=StatLine(count=saw_flop_count, total=total_hands),
        saw_turn=StatLine(count=saw_turn_count, total=total_hands),
        saw_river=StatLine(count=saw_river_count, total=total_hands),
        rfi=StatLine(count=rfi_count, total=rfi_total),
        limp=StatLine(count=limp_count, total=limp_total),
        call_open=StatLine(count=call_open_count, total=call_open_total),
        three_bet=StatLine(count=three_bet_count, total=three_bet_total),
        four_bet=StatLine(count=four_bet_count, total=four_bet_total),
        fold_to_3bet=StatLine(count=fold_3bet_count, total=fold_3bet_total),
        fold_to_4bet=StatLine(count=fold_4bet_count, total=fold_4bet_total),
        call_3bet=StatLine(count=call_3bet_count, total=call_3bet_total),
        attempt_steal=StatLine(count=steal_count, total=steal_total),
        fold_bb_to_steal=StatLine(count=fold_bb_steal_count, total=fold_bb_steal_total),
        fold_sb_to_steal=StatLine(count=fold_sb_steal_count, total=fold_sb_steal_total),
        wtsd=StatLine(count=wtsd_count, total=wtsd_total),
        wsd=StatLine(count=wsd_count, total=wsd_total),
        std_dev=std_dev,
    )
