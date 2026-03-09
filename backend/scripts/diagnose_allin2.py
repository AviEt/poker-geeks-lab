"""
Diagnostic: find all-in hands that _detect_allin might be missing.

Run: cd backend && uv run python scripts/diagnose_allin2.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.action import ActionType
from domain.street import StreetName
from parsers.ggpoker import GGPokerParser

REAL_HANDS_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "hand_histories" / "real_hands"
HERO = "Hero"


def main():
    parser = GGPokerParser()
    hand_files = sorted(REAL_HANDS_DIR.glob("*.txt"))

    all_hands = []
    for f in hand_files:
        all_hands.extend(parser.parse_file(f))

    hero_hands = [h for h in all_hands if any(p.name == HERO for p in h.players)]

    # Find hands where someone went all-in
    allin_detected = []
    allin_missed = []

    for hand in hero_hands:
        has_allin_action = False
        allin_street = None
        hero_folded = False
        folded = set()

        for street in hand.streets:
            for action in street.actions:
                if action.action_type == ActionType.FOLD:
                    folded.add(action.player_name)
                if action.is_all_in and street.name != StreetName.RIVER:
                    has_allin_action = True
                    if allin_street is None:
                        allin_street = street.name

        hero_folded = HERO in folded

        if has_allin_action:
            if hand.all_in_equity and HERO in hand.all_in_equity:
                allin_detected.append(hand)
            else:
                # This hand has an all-in but we didn't calculate equity
                player = next(p for p in hand.players if p.name == HERO)
                hero_cards = player.hole_cards

                # Check why it was missed
                active_with_cards = {
                    p.name: p.hole_cards
                    for p in hand.players
                    if p.hole_cards and p.name not in folded
                }

                reason = "unknown"
                if hero_folded:
                    reason = "Hero folded"
                elif len(active_with_cards) < 2:
                    reason = f"Not enough players with cards ({len(active_with_cards)})"
                elif HERO not in active_with_cards:
                    reason = "Hero has no cards"
                elif hand.all_in_equity and HERO not in hand.all_in_equity:
                    reason = "Equity calculated but Hero not in it"
                else:
                    reason = f"Unknown - equity={hand.all_in_equity}"

                bb = hand.big_blind
                net_bb = player.net_won / bb
                print(f"MISSED: Hand {hand.hand_id} street={allin_street} "
                      f"reason={reason} net_bb={net_bb:.2f} "
                      f"active_cards={list(active_with_cards.keys())}")
                allin_missed.append(hand)

    # Also check: are there river all-ins?
    river_allin_count = 0
    for hand in hero_hands:
        for street in hand.streets:
            if street.name == StreetName.RIVER:
                for action in street.actions:
                    if action.is_all_in and HERO not in folded:
                        river_allin_count += 1
                        break

    print(f"\n{'='*60}")
    print(f"Hero hands: {len(hero_hands)}")
    print(f"All-in detected (equity calculated): {len(allin_detected)}")
    print(f"All-in missed (has all-in action, no equity): {len(allin_missed)}")
    print(f"River all-ins (correctly excluded): {river_allin_count}")
    print(f"{'='*60}")

    # Breakdown by reason
    if allin_missed:
        print("\nMissed hands by reason:")
        from collections import Counter
        reasons = Counter()
        for hand in allin_missed:
            has_allin_action = False
            hero_folded = HERO in {
                a.player_name for s in hand.streets for a in s.actions
                if a.action_type == ActionType.FOLD
            }
            active_with_cards = {
                p.name: p.hole_cards
                for p in hand.players
                if p.hole_cards and p.name not in {
                    a.player_name for s in hand.streets for a in s.actions
                    if a.action_type == ActionType.FOLD
                }
            }
            if hero_folded:
                reasons["Hero folded"] += 1
            elif len(active_with_cards) < 2:
                reasons["Not enough players with cards"] += 1
            else:
                reasons["Other"] += 1
        for reason, count in reasons.most_common():
            print(f"  {reason}: {count}")

    # What's the total net_bb impact of missed hands?
    missed_net_bb = sum(
        next(p for p in h.players if p.name == HERO).net_won / h.big_blind
        for h in allin_missed
    )
    detected_net_bb = sum(
        next(p for p in h.players if p.name == HERO).net_won / h.big_blind
        for h in allin_detected
    )
    print(f"\nNet BB from detected all-in hands: {detected_net_bb:.2f}")
    print(f"Net BB from missed all-in hands: {missed_net_bb:.2f}")


if __name__ == "__main__":
    main()
