"""
Verify uncalled bet amounts by parsing raw text vs heuristic.

Run: cd backend && uv run python scripts/diagnose_uncalled_verify.py
"""
import re
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from treys import Card, Evaluator

from domain.action import ActionType
from domain.street import StreetName
from parsers.ggpoker import GGPokerParser

REAL_HANDS_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "hand_histories" / "real_hands"
HERO = "Hero"
_HEADER = re.compile(r"Poker Hand #RC(?P<hand_id>\d+):")
_UNCALLED = re.compile(r"Uncalled bet \(\$(?P<amount>[\d.]+)\) returned to (?P<name>.+)")
_EVALUATOR = Evaluator()
_RANKS = "23456789TJQKA"
_SUITS = "hdcs"
_ALL_CARDS = [r + s for r in _RANKS for s in _SUITS]


def exact_equity(players, board=None):
    if board is None:
        board = []
    used = set()
    for cards in players.values():
        used.update(cards)
    used.update(board)
    remaining = [c for c in _ALL_CARDS if c not in used]
    cards_needed = 5 - len(board)
    player_names = list(players.keys())
    treys_hands = {name: [Card.new(c) for c in cards] for name, cards in players.items()}
    treys_board_base = [Card.new(c) for c in board]
    wins = {name: 0.0 for name in player_names}
    total = 0
    for combo in combinations(remaining, cards_needed):
        full_board = treys_board_base + [Card.new(c) for c in combo]
        scores = {name: _EVALUATOR.evaluate(full_board, hand) for name, hand in treys_hands.items()}
        best = min(scores.values())
        winners = [n for n, s in scores.items() if s == best]
        share = 1.0 / len(winners)
        for w in winners:
            wins[w] += share
        total += 1
    return {name: wins[name] / total for name in player_names}


def main():
    parser = GGPokerParser()
    hand_files = sorted(REAL_HANDS_DIR.glob("*.txt"))

    # Build map of hand_id -> raw text uncalled bets for Hero
    raw_uncalled = {}
    for f in hand_files:
        text = f.read_text(encoding="utf-8")
        current_hand_id = None
        for line in text.splitlines():
            m = _HEADER.match(line)
            if m:
                current_hand_id = m.group("hand_id")
            m = _UNCALLED.match(line)
            if m and m.group("name") == HERO and current_hand_id:
                raw_uncalled[current_hand_id] = raw_uncalled.get(current_hand_id, 0.0) + float(m.group("amount"))

    # Parse all hands
    all_hands = []
    for f in hand_files:
        all_hands.extend(parser.parse_file(f))

    hero_hands = [h for h in all_hands if any(p.name == HERO for p in h.players)]
    allin_hands = [h for h in hero_hands if h.all_in_equity and HERO in h.all_in_equity]

    print(f"All-in hands: {len(allin_hands)}")
    print()

    # Compare uncalled amounts
    total_adj_heuristic = 0.0
    total_adj_rawtext = 0.0
    total_adj_rawtext2 = 0.0  # Using hand.pot instead of investment-based pot

    for hand in hero_hands:
        player = next(p for p in hand.players if p.name == HERO)
        bb = hand.big_blind
        net_bb = player.net_won / bb

        if not (hand.all_in_equity and HERO in hand.all_in_equity
                and hand.all_in_pot_bb is not None and hand.all_in_invested_bb is not None):
            total_adj_heuristic += net_bb
            total_adj_rawtext += net_bb
            total_adj_rawtext2 += net_bb
            continue

        pot_bb = hand.all_in_pot_bb
        inv_bb = hand.all_in_invested_bb
        rake_bb = hand.rake / bb

        # Heuristic uncalled
        heur_uncalled = _heuristic_uncalled(hand) / bb
        h_fixed_inv = inv_bb - heur_uncalled
        h_fixed_pot = pot_bb - heur_uncalled

        # Raw text uncalled
        raw_unc = raw_uncalled.get(hand.hand_id, 0.0) / bb
        r_fixed_inv = inv_bb - raw_unc
        r_fixed_pot = pot_bb - raw_unc

        # Exact equity
        folded = set()
        for street in hand.streets:
            for action in street.actions:
                if action.action_type == ActionType.FOLD:
                    folded.add(action.player_name)
        active_with_cards = {
            p.name: p.hole_cards
            for p in hand.players
            if p.hole_cards and p.name not in folded
        }
        allin_street_idx = None
        for i, street in enumerate(hand.streets):
            if street.name == StreetName.RIVER:
                break
            if any(a.is_all_in for a in street.actions):
                allin_street_idx = i
                break
        board = []
        if allin_street_idx is not None:
            for street in hand.streets[:allin_street_idx + 1]:
                if street.cards:
                    board.extend(street.cards)
        eq = exact_equity(active_with_cards, board=board if board else None)[HERO]

        adj_h = eq * (h_fixed_pot - rake_bb) - h_fixed_inv
        adj_r = eq * (r_fixed_pot - rake_bb) - r_fixed_inv

        # Strategy using hand.pot directly
        pot_from_summary_bb = hand.pot / bb
        adj_r2 = eq * (pot_from_summary_bb - rake_bb) - r_fixed_inv

        total_adj_heuristic += adj_h
        total_adj_rawtext += adj_r
        total_adj_rawtext2 += adj_r2

        if abs(heur_uncalled - raw_unc) > 0.01 or raw_unc > 0:
            print(f"Hand {hand.hand_id}: heuristic_unc={heur_uncalled:.1f} raw_unc={raw_unc:.1f} "
                  f"{'MISMATCH' if abs(heur_uncalled - raw_unc) > 0.01 else 'OK'} "
                  f"eq={eq:.4f} adj_h={adj_h:.2f} adj_r={adj_r:.2f} adj_r2={adj_r2:.2f}")

    n = len(hero_hands)
    print()
    print("=" * 70)
    print(f"BB/100 adj (heuristic uncalled + rake): {total_adj_heuristic / n * 100:.2f}")
    print(f"BB/100 adj (raw text uncalled + rake):  {total_adj_rawtext / n * 100:.2f}")
    print(f"BB/100 adj (raw text + hand.pot field): {total_adj_rawtext2 / n * 100:.2f}")
    print(f"BB/100 adj (target):                    7.74")
    print("=" * 70)


def _heuristic_uncalled(hand):
    skip = {ActionType.WINS, ActionType.SHOWS, ActionType.MUCKS}
    folded = set()
    allin_street_idx = None
    for i, street in enumerate(hand.streets):
        if street.name == StreetName.RIVER:
            break
        has_allin = False
        for action in street.actions:
            if action.action_type == ActionType.FOLD:
                folded.add(action.player_name)
            if action.is_all_in:
                has_allin = True
        if has_allin:
            allin_street_idx = i
            break
    if allin_street_idx is None:
        return 0.0
    total_invested = {}
    for street in hand.streets[:allin_street_idx + 1]:
        street_invested = {}
        for action in street.actions:
            if not action.amount or action.action_type in skip:
                continue
            if action.action_type == ActionType.RAISE:
                street_invested[action.player_name] = action.amount
            else:
                street_invested[action.player_name] = (
                    street_invested.get(action.player_name, 0.0) + action.amount
                )
        for name, amount in street_invested.items():
            total_invested[name] = total_invested.get(name, 0.0) + amount
    hero_invested = total_invested.get(HERO, 0.0)
    active = {
        p.name for p in hand.players
        if p.hole_cards and p.name not in folded and p.name != HERO
    }
    if not active:
        return 0.0
    max_opp = max(total_invested.get(n, 0.0) for n in active if n in total_invested)
    return max(0.0, hero_invested - max_opp)


if __name__ == "__main__":
    main()
