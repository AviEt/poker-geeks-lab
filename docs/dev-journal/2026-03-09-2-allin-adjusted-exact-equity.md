# Session: All-In Adjusted BB/100 — Exact Equity and a New Ground Truth

## What I tried to accomplish

The previous session had identified two bugs in the all-in adjusted BB/100 calculation and confirmed their impact through diagnostic scripts, but hadn't implemented the fixes. This session picked up from there: apply the two fixes, then use the PT4 database as a lens to understand the remaining gap and decide what the correct target should be — without treating PT4 as a permanent dependency.

## How the session unfolded

### Applying the two confirmed fixes

The session resumed mid-stride. Two bugs were already diagnosed:

1. **Uncalled bet inflation** — when Hero raised more than an opponent could call, the parser tracked Hero's full raise amount as their investment even though the excess was returned. This inflated both the pot and Hero's investment, systematically overstating the adjusted result.

2. **Missing rake subtraction** — the formula was `equity × pot − investment` instead of the PT4-correct `equity × (pot − rake) − investment`. PT4 documentation had confirmed that rake is subtracted from the pot before applying equity.

The fixes were straightforward in code: cap `hero_investment` at the maximum active opponent's investment (the uncalled excess was never really in play), and subtract `rake_bb` from `all_in_pot_bb` in the stats formula. Both went in cleanly, all 157 existing tests passed, and the sanity test confirmed the non-adjusted stats were untouched.

But the adjusted result came out at **~8.02 BB/100** — still off from the PT4 target of **7.74**.

### Querying the PT4 database

Rather than continuing to guess at the remaining gap, the user made a decisive move:

> *"let's continue but let's do it in steps. I want you to use the knowledge you accumulated so far in this conversation but change direction - check the PT 4 DB. It's on localhost port 5432 Database PT4_2026_03_08_155912 DB name PGL_test. See how the hands you found are represented there and if you can make something out of it and then return and tell me what you found before you continue to fix anything"*

This was a key moment. Instead of continuing to debug blindly, the user wanted direct access to PT4's internal representation — then a report before any further code changes. The instruction to stop and report before continuing shaped the rest of the session.

Connecting to the database via psycopg2, the key table was `cash_hand_player_statistics` with two critical columns: `amt_won` (actual result) and `amt_expected_won` (PT4's adjusted result). PT4 flags all-in adjusted hands simply by having those two values differ.

PT4 identifies **20 all-in adjusted hands** for Hero. We were detecting **21**. The overlap was 19, with one hand PT4 adjusts that we don't (a river all-in split pot), and two we adjust that PT4 doesn't (hands where one player had 100% equity — deterministic outcomes).

Reverse-engineering PT4's formula from the database confirmed: **`equity × (pot − rake − jackpot_fee − mgr_fee) − total_bet`**. The first two fee components matched our `hand.rake` exactly. The third — `amt_mgr` — was the mystery.

### Tracking down the phantom fee

The `amt_mgr` column showed small additional deductions: $0.05 on bigger pots, $0.02-$0.03 on smaller ones. But checking the raw hand history text was revealing — the winner's collected amount balanced perfectly against `pot − rake − jackpot`. There was no room for `amt_mgr` in the actual money flow. It's a PT4 internal calculation, not a real GGPoker fee.

Still, the formula was reverse-engineered: `mgr = (rake_cents + 3) // 6` (integer floor division with a 3-cent offset). Perfect match on all 28 unique rake values observed. Even with PT4's own stored equity values and this formula, we got **7.88** — still not 7.74. The remaining 0.14 BB/100 was pure equity precision: PT4 uses higher internal precision than the 4 decimal places stored in `val_equity`.

The breakdown was clear: 0.14 from the phantom mgr fee, 0.14 from PT4 internal equity rounding, 0.02 from a river all-in we skip. Total gap: ~0.28 BB/100.

### The pivotal decision

The user asked whether we could close the gap from the DB alone, prompting analysis of what it would take. The answer: we could derive `amt_mgr` from the formula, but the equity precision gap would remain. Matching PT4 exactly required reading from the PT4 database at calculation time.

The user's response reframed everything:

> *"I don't want PT4 to be our source of truth. I want to develop something new. What do you suggest?"*

This changed the frame of the entire problem. PT4's 7.74 was built on a fee that doesn't appear in GGPoker's hand histories. If we're computing from actual hand data, our formula using real fees is *more correct* than PT4's — it just produces a different number. The target shouldn't be 7.74; it should be whatever our correct calculation produces.

The recommendation that followed:

1. **Switch to exact equity enumeration** — eliminates the ±0.15 BB/100 Monte Carlo noise entirely. With only ~20 all-in hands across 4,447 total, exact enumeration is computationally feasible.
2. **Skip hands with 0% or 100% equity** — deterministic outcomes don't need adjustment; actual result equals expected result.
3. **Update the sanity test target** to whatever exact enumeration produces, then lock it in.

### Implementation

The TDD workflow required writing failing tests first:

- `test_allin_equity_is_deterministic` — parse the same hand twice, assert identical equity values. Monte Carlo would fail this; exact enumeration passes it.
- `test_deterministic_outcome_not_marked_as_allin` — a real hand (RC2030688727, where Hero's 9h Ah was ahead of QdJh with 100% equity on the turn) should have `all_in_equity = None` after parsing.

Both tests failed as expected against the MC implementation.

Replacing Monte Carlo with `itertools.combinations` in `equity.py` was a two-line conceptual change: swap `random.sample` for `combinations`, accumulate over all run-outs instead of sampling. Then in `_detect_allin`, after computing equity, a single guard: if any player's equity is exactly 0.0 or 1.0, return `None` instead.

Both new tests passed. The deterministic outcome test confirmed that exact equity of 1.0 for hero triggered the skip. The determinism test used a new turn all-in fixture (44 combinations, essentially instant) rather than the preflop fixture (1.7M combinations, ~50 seconds).

One performance issue surfaced: the module-scoped preflop fixture was still computing equity once, but the `test_deterministic_outcome_not_marked_as_allin` test had to parse all 4,447 real hands to find hand RC2030688727 — taking several minutes. The fix was promoting the preflop fixture to `scope="module"` so the 1.7M-combo enumeration runs only once across all tests that use it.

Running compute_stats on all real hands produced: **8.0212 BB/100 adjusted**, deterministic to 4 decimal places. The sanity test was uncommented and updated.

## Key prompts that moved things forward

> *"let's continue but let's do it in steps. I want you to use the knowledge you accumulated so far in this conversation but change direction - check the PT 4 DB. It's on localhost port 5432 Database PT4_2026_03_08_155912 DB name PGL_test. See how the hands you found are represented there and if you can make something out of it and then return and tell me what you found before you continue to fix anything"*

This broke the debugging loop and introduced external ground truth. The instruction to stop and report before continuing prevented premature fixes.

> *"I don't want PT4 to be our source of truth. I want to develop something new. What do you suggest?"*

This reframed the whole problem. Instead of chasing PT4's 7.74, we accepted that PT4 uses a phantom fee not in the hand data and decided our formula using actual GGPoker fees is the correct one. A philosophical shift that unlocked the path forward.

> *"yes, let's do it"*

Simple approval of the three-point plan. Sometimes the most important prompt is just clearing the way.

## Important decisions made

**Exact enumeration over Monte Carlo.** The original MC approach was a pragmatic choice — 10K samples gives ~0.5% accuracy and runs fast. But for a metric that aggregates over only ~20 all-in hands, the noise is non-trivial at the session level (~±0.15 BB/100). Exact enumeration eliminates this entirely and makes the stat reproducible. The cost is computation time at parse time, which is acceptable since parsing happens once on import.

**Our target is 8.02, not 7.74.** PT4's number includes `amt_mgr`, a fee it computes internally from a formula `(rake_cents + 3) // 6` that has no basis in GGPoker's actual hand history data. Using actual fees is more defensible. We set our own ground truth.

**Skip 0/1 equity hands.** This was PT4's implicit behavior (RC2030688727 and RC2031160058 had `amt_expected_won = amt_won` in PT4's DB). When one player has 100% equity, the "adjustment" produces the same number as actual, so no adjustment is needed. Making this explicit prevents spurious all-in detection.

**Module-scoped fixture for preflop equity.** The preflop fixture (AA vs KK, ~1.7M combos) was being recomputed per test function. Promoting to `scope="module"` made the expensive computation run once per test session, shrinking the test class from ~9 minutes to ~5 minutes.

**Turn all-in fixture for the determinism test.** Using 44 combinations instead of 1.7M for a test whose purpose is just to verify determinism — not to check a specific equity value — keeps the test fast and focused.

## Takeaways

The PT4 database was an unexpectedly useful tool for understanding the *shape* of the problem, even without treating it as a dependency. Seeing which hands PT4 adjusts (and which it skips) revealed the 0/1 equity rule. Seeing the `amt_mgr` column led to understanding what we were missing — and ultimately to the decision to not chase it.

The "stop and report before continuing" instruction was well-placed. It prevented implementing a fix for a gap that turned out to be a phantom fee from a tool we weren't going to depend on.

Exact enumeration and Monte Carlo produce the same aggregate result in expectation — but exact enumeration makes the stat a pure function of the hand history data, which matters for a sanity test. MC would need a fixed seed to be testable, which is a code smell. Exact enumeration is simply the right approach for this scale.

## Next direction

The adjusted BB/100 stat is now implemented correctly and locked in at 8.02. Likely next steps:

- Surface `bb_per_100_adjusted` in the frontend stats panel
- Consider whether to show both metrics or just the adjusted one
- Begin working on additional stats (3-bet%, cbet%, fold to cbet, etc.)
- Potentially investigate whether the river all-in case (RC2029897330, split pot) should be handled — it contributes ~0.02 BB/100 and would require detecting river all-ins, which we currently skip
