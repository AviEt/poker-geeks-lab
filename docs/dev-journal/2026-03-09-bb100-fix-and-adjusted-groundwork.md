# BB/100 Fix and All-in Adjusted Groundwork

## What I tried to accomplish

This session was the tail end of a long overnight run to fix BB/100 and BB/100 all-in adjusted calculations. The previous session had already solved BB/100 (13.1 matching the sanity test expectation) through two parser fixes — parsing GGPoker's "Bet & Muck" action format and correcting how cashout risk affects net_won. It also made significant progress on BB/100 adjusted, testing multiple pot/investment/rake calculation strategies, but couldn't close the last 0.24 BB/100 gap (7.98 vs expected 7.74).

This session picked up where context ran out. The goal was to stabilize what works (BB/100), defer what doesn't yet (adjusted), and make sure all tests pass.

## How the session unfolded

The user came back and asked me to explain what I'd gotten stuck on. The core issue was the all-in adjusted formula — specifically how to calculate the "main pot" and "hero investment" for PT4's `equity x pot - investment` formula. I'd tested six different strategies combining three variables: pot capping method, investment figure, and whether to subtract rake. The best result was 7.98 using effective cap + effective investment + rake subtraction, but none hit exactly 7.74.

The user then asked a practical question: "If I run e2e tests now - does the code work perfectly for BB/100 but not BB/100 adj?" I checked the actual code state — confirmed BB/100 was correct, adjusted would be wrong (~6.53 with the hero_cap strategy still in the code), but both assertions were commented out in the sanity test so it would pass.

This led to the key decision. Rather than continue grinding on the adjusted formula, the user said to split the work: ship BB/100 now, come back to adjusted later.

I uncommented the BB/100 test assertion, ran the sanity test (all 4 tests passed including the new one), then ran the full test suite. Five unit tests failed — all consequences of changes made during the overnight session that hadn't been reconciled with the existing test expectations.

The failures were:

1. **Net won accounting test** — the cashout risk fix stopped subtracting cashout risk from net_won (correct for BB/100 per PT4), but the money-flow test still expected it in the total. Fix: remove cashout_risk from the expected formula since it's no longer in net_won.

2. **All-in pot BB test** — the field's semantics changed from "net potential win" (old: pot minus hero investment) to "total main pot" (new: full pot). Both players invested $12 at $0.10 BB, so it went from expecting 120bb to 240bb. The new formula needs pot and investment as separate values.

3. **Three adjusted stats unit tests** — these set `all_in_pot_bb` but not the new `all_in_invested_bb` field, so the stats code fell through to using actual net_won instead of the equity formula. Fixed by setting `all_in_invested_bb` and recalculating expected values with the PT4 formula (`equity x pot - investment`).

After fixing all five, the full suite passed: 157 tests green.

## Key prompts that moved things forward

> "If I run e2e tests now - does the code work perfectly for BB/100 but not BB/100 adj?"

This forced me to check the actual code state rather than assumptions from the previous session. It revealed that both assertions were commented out, which meant the sanity test would pass trivially.

> "Lets split the work for now - fix the code to support normal bb/100 - leave the adjusted commented out. We'll get back to it later when I have more time to dive into it with you"

This was the session's turning point. Instead of continuing to chase the adjusted formula, the user pragmatically split the deliverable. Ship what's proven, defer what needs more investigation.

## Important decisions made

- **BB/100 is now a tested, enforced stat** — the sanity test assertion is uncommented and passes at exactly 13.1.
- **BB/100 adjusted remains deferred** — the sanity test assertion stays commented out. The formula infrastructure is in place (equity detection, pot/investment tracking, the stats formula), but the exact pot calculation strategy needs more work to close the 0.24 gap.
- **`all_in_pot_bb` semantics changed** — from "net potential win" to "total main pot in BB". A separate `all_in_invested_bb` field now holds hero's investment. This matches PT4's formula: `equity x pot - investment`.
- **Cashout risk excluded from net_won** — PT4 treats it as a rake-like fee that doesn't affect winrate. The accounting test was updated to reflect this.

## Takeaways

- When an overnight autonomous session runs out of context, the most productive thing the user can do is triage: what's done vs what's not, and whether to keep pushing or ship what works.
- Changing the semantics of a field (pot_bb from "net potential" to "total pot") has ripple effects across unit tests. All tests touching that field needed updating, not just the ones that originally failed.
- The five test failures were all internally consistent — they all stemmed from two root changes (cashout risk handling and pot/investment split) that the overnight session implemented but didn't fully reconcile with existing tests.

## Next direction

- **Close the BB/100 adjusted gap**: The best strategy (eff_cap + eff_inv + rake) gives 7.98 vs expected 7.74. The 0.24 difference could be Monte Carlo variance (10K equity samples), edge cases in all-in detection, or a formula nuance in how PT4 handles multi-way pots or run-it-twice. Increasing Monte Carlo samples or seeding the RNG would help isolate variance from formula errors.
- **DB migration**: The new `allin_invested_bb` column needs an Alembic migration for the production database.
- **Re-import after deploy**: Existing hands in the DB don't have the new field populated. A re-import or backfill would be needed.
