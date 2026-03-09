"""
Diagnostic: use EXACT equity enumeration (not Monte Carlo) to isolate equity errors.

Run: cd backend && uv run python scripts/diagnose_exact.py
"""
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
_EVALUATOR = Evaluator()
_RANKS = "23456789TJQKA"
_SUITS = "hdcs"
_ALL_CARDS = [r + s for r in _RANKS for s in _SUITS]


def exact_equity(players: dict[str, list[str]], board: list[str] | None = None) -> dict[str, float]:
    """Calculate EXACT equity via full enumeration."""
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


def get_uncalled(hand, parser):
    """Calculate uncalled bet for Hero."""
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


def main():
    parser = GGPokerParser()
    hand_files = sorted(REAL_HANDS_DIR.glob("*.txt"))
    print(f"Loading {len(hand_files)} files...")

    all_hands = []
    for f in hand_files:
        all_hands.extend(parser.parse_file(f))

    hero_hands = [h for h in all_hands if any(p.name == HERO for p in h.players)]
    allin_hands = [h for h in hero_hands if h.all_in_equity and HERO in h.all_in_equity]

    print(f"Total hands: {len(hero_hands)}")
    print(f"All-in hands: {len(allin_hands)}")
    print()

    total_net_bb = 0.0
    total_adj_mc = 0.0   # Monte Carlo equity (from parser)
    total_adj_exact = 0.0  # Exact equity

    print(f"{'HandID':<15} {'MC_Eq':>7} {'Exact_Eq':>9} {'Diff':>7} {'PotBB':>8} {'InvBB':>8} {'UncBB':>8} {'RakeBB':>8} {'MC_Adj':>9} {'Exact_Adj':>10}")
    print("-" * 110)

    for hand in hero_hands:
        player = next(p for p in hand.players if p.name == HERO)
        bb = hand.big_blind
        net_bb = player.net_won / bb
        total_net_bb += net_bb

        if hand.all_in_equity and HERO in hand.all_in_equity and hand.all_in_pot_bb is not None and hand.all_in_invested_bb is not None:
            mc_eq = hand.all_in_equity[HERO]
            pot_bb = hand.all_in_pot_bb
            inv_bb = hand.all_in_invested_bb
            rake_bb = hand.rake / bb
            uncalled_bb = get_uncalled(hand, parser) / bb

            fixed_inv_bb = inv_bb - uncalled_bb
            fixed_pot_bb = pot_bb - uncalled_bb

            # Monte Carlo adjusted (with both fixes)
            mc_adj = mc_eq * (fixed_pot_bb - rake_bb) - fixed_inv_bb
            total_adj_mc += mc_adj

            # Get players with known cards for exact equity
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

            # Find board at all-in point
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

            # Calculate exact equity
            exact_eq_dict = exact_equity(active_with_cards, board=board if board else None)
            exact_eq = exact_eq_dict[HERO]

            exact_adj = exact_eq * (fixed_pot_bb - rake_bb) - fixed_inv_bb
            total_adj_exact += exact_adj

            diff = mc_eq - exact_eq
            print(f"{hand.hand_id:<15} {mc_eq:>7.4f} {exact_eq:>9.4f} {diff:>+7.4f} "
                  f"{fixed_pot_bb:>8.1f} {fixed_inv_bb:>8.1f} {uncalled_bb:>8.1f} {rake_bb:>8.1f} "
                  f"{mc_adj:>9.2f} {exact_adj:>10.2f}")
        else:
            total_adj_mc += net_bb
            total_adj_exact += net_bb

    n = len(hero_hands)
    print()
    print("=" * 70)
    print(f"BB/100 (actual):                    {total_net_bb / n * 100:.2f}")
    print(f"BB/100 adj (MC + uncalled + rake):  {total_adj_mc / n * 100:.2f}")
    print(f"BB/100 adj (EXACT + uncalled + rake): {total_adj_exact / n * 100:.2f}")
    print(f"BB/100 adj (target):                7.74")
    print(f"Total MC-Exact diff:                {(total_adj_mc - total_adj_exact) / n * 100:.4f} BB/100")
    print("=" * 70)


if __name__ == "__main__":
    main()
