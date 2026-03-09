"""
Diagnostic: check cashout hands and compare equity vs GGPoker's implied equity.
Also check if any cashout hands are among detected all-in hands.

Run: cd backend && uv run python scripts/diagnose_cashout.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsers.ggpoker import GGPokerParser

REAL_HANDS_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "hand_histories" / "real_hands"
HERO = "Hero"

_HEADER = re.compile(r"Poker Hand #RC(?P<hand_id>\d+):")
_CASHOUT_CHOOSE = re.compile(r"(?P<name>.+?): Chooses to EV Cashout")
_CASHOUT_RISK = re.compile(r"(?P<name>.+?): Pays Cashout Risk \(\$(?P<amount>[\d.]+)\)")


def main():
    parser = GGPokerParser()
    hand_files = sorted(REAL_HANDS_DIR.glob("*.txt"))

    # First, find all Hero cashout hand IDs from raw text
    cashout_hand_ids = set()
    for f in hand_files:
        text = f.read_text(encoding="utf-8")
        current_hand_id = None
        hero_cashout = False
        for line in text.splitlines():
            m = _HEADER.match(line)
            if m:
                if hero_cashout and current_hand_id:
                    cashout_hand_ids.add(current_hand_id)
                current_hand_id = m.group("hand_id")
                hero_cashout = False
            m = _CASHOUT_CHOOSE.match(line)
            if m and m.group("name") == HERO:
                hero_cashout = True
        if hero_cashout and current_hand_id:
            cashout_hand_ids.add(current_hand_id)

    print(f"Hero EV Cashout hand IDs: {sorted(cashout_hand_ids)}")

    # Now parse all hands
    all_hands = []
    for f in hand_files:
        all_hands.extend(parser.parse_file(f))

    hero_hands = [h for h in all_hands if any(p.name == HERO for p in h.players)]
    allin_hands = [h for h in hero_hands if h.all_in_equity and HERO in h.all_in_equity]
    allin_ids = {h.hand_id for h in allin_hands}

    print(f"\nDetected all-in hand IDs: {sorted(allin_ids)}")
    overlap = cashout_hand_ids & allin_ids
    print(f"\nOverlap (cashout + detected): {sorted(overlap)}")
    print(f"Cashout but NOT detected: {sorted(cashout_hand_ids - allin_ids)}")

    # For cashout hands that ARE detected, compare equities
    if overlap:
        print(f"\nCashout hands in detected set:")
        for hand in allin_hands:
            if hand.hand_id in overlap:
                eq = hand.all_in_equity[HERO]
                pot_bb = hand.all_in_pot_bb
                inv_bb = hand.all_in_invested_bb
                rake_bb = hand.rake / hand.big_blind
                cr = hand.cashout_risk
                cr_bb = cr / hand.big_blind
                print(f"  Hand {hand.hand_id}: eq={eq:.4f} cashout_risk=${cr:.2f} ({cr_bb:.1f} BB)")

    # For cashout hands NOT detected, show why
    if cashout_hand_ids - allin_ids:
        print(f"\nCashout hands NOT in detected set:")
        for hand in hero_hands:
            if hand.hand_id in (cashout_hand_ids - allin_ids):
                player = next(p for p in hand.players if p.name == HERO)
                net_bb = player.net_won / hand.big_blind
                eq = hand.all_in_equity
                pot_bb = hand.all_in_pot_bb
                cr = hand.cashout_risk
                print(f"  Hand {hand.hand_id}: net_bb={net_bb:.2f} all_in_eq={eq} "
                      f"pot_bb={pot_bb} cashout_risk=${cr:.2f}")

    # Also check: for ALL hands, print cash_drop to see if any all-in hands have it
    allin_with_cashdrop = [h for h in allin_hands if h.cash_drop > 0]
    print(f"\nAll-in hands with cash_drop > 0: {len(allin_with_cashdrop)}")
    for h in allin_with_cashdrop:
        print(f"  Hand {h.hand_id}: cash_drop=${h.cash_drop:.2f}")


if __name__ == "__main__":
    main()
