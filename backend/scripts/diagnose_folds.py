"""
Diagnostic: check if any detected all-in hands have post-all-in folds.
PT4 excludes hands where players folded after an all-in (selection bias).

Run: cd backend && uv run python scripts/diagnose_folds.py
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


def get_uncalled(hand):
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
    all_hands = []
    for f in hand_files:
        all_hands.extend(parser.parse_file(f))

    hero_hands = [h for h in all_hands if any(p.name == HERO for p in h.players)]
    allin_hands = [h for h in hero_hands if h.all_in_equity and HERO in h.all_in_equity]

    print(f"Checking {len(allin_hands)} all-in hands for post-all-in folds...")
    print()

    hands_with_post_allin_folds = []
    hands_clean = []

    total_adj_exact_all = 0.0
    total_adj_exact_clean = 0.0
    total_non_allin = 0.0

    for hand in hero_hands:
        player = next(p for p in hand.players if p.name == HERO)
        bb = hand.big_blind
        net_bb = player.net_won / bb

        if not (hand.all_in_equity and HERO in hand.all_in_equity
                and hand.all_in_pot_bb is not None and hand.all_in_invested_bb is not None):
            total_adj_exact_all += net_bb
            total_adj_exact_clean += net_bb
            total_non_allin += net_bb
            continue

        # Find all-in street and check for post-all-in folds
        has_post_allin_fold = False
        post_allin_folders = []
        allin_street_idx = None
        folded_before_allin = set()
        folded_all = set()

        for i, street in enumerate(hand.streets):
            if street.name == StreetName.RIVER:
                break
            allin_seen = False
            for action in street.actions:
                if action.action_type == ActionType.FOLD:
                    folded_all.add(action.player_name)
                    if allin_seen:
                        has_post_allin_fold = True
                        post_allin_folders.append(action.player_name)
                    else:
                        folded_before_allin.add(action.player_name)
                if action.is_all_in:
                    allin_seen = True
            if allin_seen:
                allin_street_idx = i
                break
            # Track folds on pre-all-in streets too
            for action in street.actions:
                if action.action_type == ActionType.FOLD:
                    folded_before_allin.add(action.player_name)

        # Calculate exact equity
        active_with_cards = {
            p.name: p.hole_cards
            for p in hand.players
            if p.hole_cards and p.name not in folded_all
        }
        board = []
        if allin_street_idx is not None:
            for street in hand.streets[:allin_street_idx + 1]:
                if street.cards:
                    board.extend(street.cards)
        exact_eq_dict = exact_equity(active_with_cards, board=board if board else None)
        exact_eq = exact_eq_dict[HERO]

        pot_bb = hand.all_in_pot_bb
        inv_bb = hand.all_in_invested_bb
        rake_bb = hand.rake / bb
        uncalled_bb = get_uncalled(hand) / bb
        fixed_inv_bb = inv_bb - uncalled_bb
        fixed_pot_bb = pot_bb - uncalled_bb
        adj = exact_eq * (fixed_pot_bb - rake_bb) - fixed_inv_bb

        total_adj_exact_all += adj

        if has_post_allin_fold:
            # PT4 would use actual net_won for this hand
            total_adj_exact_clean += net_bb
            hands_with_post_allin_folds.append(hand)
            print(f"POST-ALLIN FOLD: Hand {hand.hand_id} folders={post_allin_folders} "
                  f"eq={exact_eq:.4f} adj={adj:.2f} net_bb={net_bb:.2f} diff={net_bb - adj:.2f}")
        else:
            total_adj_exact_clean += adj
            hands_clean.append(hand)

    n = len(hero_hands)
    print(f"\n{'='*70}")
    print(f"Hands with post-all-in folds: {len(hands_with_post_allin_folds)}")
    print(f"Clean all-in hands: {len(hands_clean)}")
    print(f"BB/100 adj (all all-in, exact eq):     {total_adj_exact_all / n * 100:.2f}")
    print(f"BB/100 adj (exclude post-fold, actual): {total_adj_exact_clean / n * 100:.2f}")
    print(f"BB/100 adj (target):                    7.74")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
