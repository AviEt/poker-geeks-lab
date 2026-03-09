"""
Diagnostic script: analyze all-in hands and compare adjusted BB/100 strategies.

Run: cd backend && uv run python scripts/diagnose_allin.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsers.ggpoker import GGPokerParser

REAL_HANDS_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "hand_histories" / "real_hands"
HERO = "Hero"
_UNCALLED = re.compile(r"Uncalled bet \(\$(?P<amount>[\d.]+)\) returned to (?P<name>.+)")


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
    print(f"All-in hands with equity: {len(allin_hands)}")
    print()

    # Strategy comparison
    total_net_bb = 0.0
    total_adj_current = 0.0  # equity * pot_bb - invested_bb (current code)
    total_adj_rake = 0.0     # equity * (pot_bb - rake_bb) - invested_bb
    total_adj_all_fees = 0.0 # equity * (pot_bb - all_fees_bb) - invested_bb
    total_adj_uncalled = 0.0 # fix uncalled bet in investment, no rake sub
    total_adj_both = 0.0     # fix uncalled + subtract all fees
    total_adj_pot_field = 0.0  # use hand.pot - hand.rake from summary line

    for hand in hero_hands:
        player = next(p for p in hand.players if p.name == HERO)
        bb = hand.big_blind
        net_bb = player.net_won / bb
        total_net_bb += net_bb

        if hand.all_in_equity and HERO in hand.all_in_equity and hand.all_in_pot_bb is not None and hand.all_in_invested_bb is not None:
            eq = hand.all_in_equity[HERO]
            pot_bb = hand.all_in_pot_bb
            inv_bb = hand.all_in_invested_bb
            rake_bb = hand.rake / bb

            # Check for uncalled bets in this hand (scan raw text)
            # We need to find uncalled bets returned to Hero
            # Parse the hand file to get uncalled info
            uncalled_hero = _get_uncalled_for_hero(hand, parser)
            uncalled_bb = uncalled_hero / bb

            # Current formula (no rake, no uncalled fix)
            adj_current = eq * pot_bb - inv_bb
            total_adj_current += adj_current

            # With rake subtraction only
            adj_rake = eq * (pot_bb - rake_bb) - inv_bb
            total_adj_rake += adj_rake

            # With all fees subtraction (rake field already includes all fees)
            adj_all_fees = eq * (pot_bb - rake_bb) - inv_bb
            total_adj_all_fees += adj_all_fees

            # With uncalled bet fix only (no rake)
            fixed_inv_bb = inv_bb - uncalled_bb
            fixed_pot_bb = pot_bb - uncalled_bb  # pot also shrinks by uncalled amount
            adj_uncalled = eq * fixed_pot_bb - fixed_inv_bb
            total_adj_uncalled += adj_uncalled

            # With BOTH fixes: uncalled + all fees
            adj_both = eq * (fixed_pot_bb - rake_bb) - fixed_inv_bb
            total_adj_both += adj_both

            # Using hand.pot - hand.rake directly (no investment-based pot)
            pot_after_rake_bb = (hand.pot - hand.rake) / bb
            adj_pot_field = eq * pot_after_rake_bb - fixed_inv_bb
            total_adj_pot_field += adj_pot_field

            if uncalled_bb > 0:
                print(f"  Hand {hand.hand_id}: eq={eq:.3f} pot_bb={pot_bb:.1f} inv_bb={inv_bb:.1f} "
                      f"uncalled_bb={uncalled_bb:.1f} rake_bb={rake_bb:.1f} "
                      f"adj_current={adj_current:.2f} adj_both={adj_both:.2f} adj_pot_field={adj_pot_field:.2f}")
        else:
            total_adj_current += net_bb
            total_adj_rake += net_bb
            total_adj_all_fees += net_bb
            total_adj_uncalled += net_bb
            total_adj_both += net_bb
            total_adj_pot_field += net_bb

    n = len(hero_hands)
    print()
    print("=" * 70)
    print(f"BB/100 (actual):                    {total_net_bb / n * 100:.2f}  (expect 13.1)")
    print(f"BB/100 adj (current - no fixes):    {total_adj_current / n * 100:.2f}")
    print(f"BB/100 adj (rake sub only):         {total_adj_rake / n * 100:.2f}")
    print(f"BB/100 adj (uncalled fix only):     {total_adj_uncalled / n * 100:.2f}")
    print(f"BB/100 adj (uncalled + rake):       {total_adj_both / n * 100:.2f}")
    print(f"BB/100 adj (hand.pot field + uncalled): {total_adj_pot_field / n * 100:.2f}")
    print(f"BB/100 adj (target):                7.74")
    print("=" * 70)

    # Also print all-in hand details
    print(f"\nAll-in hands detail:")
    print(f"{'HandID':<15} {'Equity':>7} {'PotBB':>8} {'InvBB':>8} {'UncBB':>8} {'RakeBB':>8} {'AdjCurr':>9} {'AdjBoth':>9} {'AdjPot':>9} {'NetBB':>9}")
    print("-" * 110)
    for hand in allin_hands:
        player = next(p for p in hand.players if p.name == HERO)
        bb = hand.big_blind
        eq = hand.all_in_equity[HERO]
        pot_bb = hand.all_in_pot_bb
        inv_bb = hand.all_in_invested_bb
        rake_bb = hand.rake / bb
        uncalled_hero = _get_uncalled_for_hero(hand, parser)
        uncalled_bb = uncalled_hero / bb
        net_bb = player.net_won / bb
        fixed_inv_bb = inv_bb - uncalled_bb
        fixed_pot_bb = pot_bb - uncalled_bb
        adj_current = eq * pot_bb - inv_bb
        adj_both = eq * (fixed_pot_bb - rake_bb) - fixed_inv_bb
        pot_after_rake_bb = (hand.pot - hand.rake) / bb
        adj_pot = eq * pot_after_rake_bb - fixed_inv_bb
        print(f"{hand.hand_id:<15} {eq:>7.3f} {pot_bb:>8.1f} {inv_bb:>8.1f} {uncalled_bb:>8.1f} {rake_bb:>8.1f} {adj_current:>9.2f} {adj_both:>9.2f} {adj_pot:>9.2f} {net_bb:>9.2f}")


def _get_uncalled_for_hero(hand, parser):
    """Find uncalled bet amount returned to Hero in this hand.

    We need to reconstruct this from the hand data. Since the parser doesn't
    store uncalled info on the Hand object, we use a heuristic:
    compare the _detect_allin investment with what's actually in the pot.

    Simpler approach: re-read the file and find uncalled bets.
    But we don't have the file path stored. So let's calculate it:

    The uncalled bet = hero's total action investment - hero's actual pot contribution.
    Hero's actual pot contribution can be inferred from the fact that in a heads-up
    all-in, hero can't contribute more than the opponent's total investment.
    """
    # Actually, let's compute it differently:
    # The hand.pot (from summary line) = total money in the pot including all investments.
    # sum of investments = hand.pot (before rake, they should match).
    # If our investment tracking gives more than hand.pot for hero, the difference is uncalled.

    # But we need access to the _detect_allin's total_invested, which we don't have here.
    # Let's recalculate it.
    from domain.action import ActionType
    from domain.street import StreetName

    skip = {ActionType.WINS, ActionType.SHOWS, ActionType.MUCKS}
    streets = hand.streets

    # Find all-in street
    folded = set()
    allin_street_idx = None
    for i, street in enumerate(streets):
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

    # Compute total invested (same logic as _detect_allin)
    total_invested = {}
    for street in streets[:allin_street_idx + 1]:
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

    # The maximum hero can have in the pot is determined by the all-in amounts.
    # Find the all-in player's total investment:
    # In a heads-up all-in where opponent is all-in for less, hero's effective
    # investment = opponent's total investment (the rest is returned as uncalled).
    # In multi-way, it's more complex but we'll use the minimum all-in amount.

    # Actually, let's use a different approach: the sum of all investments should
    # equal hand.pot (the total pot before rake). Any excess from hero is uncalled.
    sum_invested = sum(total_invested.values())

    # But sum_invested might not equal hand.pot due to:
    # 1. Uncalled bets (sum_invested > hand.pot)
    # 2. Cash drop (hand.pot > sum_invested)
    # 3. Actions after the all-in street that we're not counting

    # Better approach: just find the max opponent investment and cap hero there.
    # In a standard all-in, hero can't have more in the pot than the biggest
    # opponent stack that called/went all-in.

    active = {
        name for name, p in {pp.name: pp for pp in hand.players}.items()
        if p.hole_cards and name not in folded and name != HERO
    }

    if not active:
        return 0.0

    max_opponent_invested = max(total_invested.get(name, 0.0) for name in active if name in total_invested)

    # Uncalled = hero's excess over max opponent investment
    # But only if hero invested MORE than the max opponent
    if hero_invested > max_opponent_invested:
        return hero_invested - max_opponent_invested
    return 0.0


if __name__ == "__main__":
    main()
