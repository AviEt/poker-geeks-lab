# Sanity Test Triage — Getting the Basics Green

## What I tried to accomplish

This session was a continuation of a long-running effort to get the E2E sanity test passing. The sanity test imports all 4,447 real GGPoker hand histories and asserts exact aggregate stats against PokerTracker4 ground truth: hand count, VPIP, PFR, BB/100, and all-in adjusted BB/100.

Previous sessions had fixed VPIP/PFR walk-denominator logic (only exclude walks where Hero IS the BB, per PT4 definition), fixed API rounding precision, added cashout risk parsing, and restricted all-in equity detection to Hero-specific all-ins. But BB/100 was still failing — 10.67 vs expected 13.1 — and investigation had stalled.

The goal was to stop spinning on the hard metric and lock in what was already working.

## How the session unfolded

This session was essentially a triage decision. Coming in, Claude was deep in the BB/100 investigation — the cashout risk deduction was overshooting (10.67) while removing it entirely overshot the other way (17.04). The user had provided a key insight about mixed stakes (2,752 hands at 5NL, the rest at 10NL) suggesting the diagnostic computations from the previous session might have used a single fixed big blind rather than per-hand normalization.

But before that rabbit hole could be explored further, the user made a practical call: stop chasing the hard metrics and just ship what works.

The BB/100 and all-in adjusted tests were commented out, leaving only hand count, VPIP, and PFR. All three sanity tests passed. All 156 unit tests passed. Clean state.

## Key prompts that moved things forward

> "I see you're having trouble with the adjusted win-rate. I suggest we start first with the test for the other metrics, which are easier. Comment out the adjusted result and test everything else. What this is ready will focus on the adjusted."

This was from the previous session — the first triage decision that deferred the all-in adjusted metric.

> "Let's not get into this, I will later give you a task to calculate. Let's just start with the basic stats: 1. Number of hands 2. VPIP 3. PFR. Have those tested e2e - remove the bb/100 metrics for now. Let's start simple. Later at night I will allow you to run the entire night to figure this out."

The second triage — now also deferring BB/100. The user recognized this needed dedicated deep investigation rather than incremental debugging across short sessions.

> "I think the problem is from the hands being in different stakes. Some of them are 5nl and some 10nl. There are 2752 hands 5nl and the rest are 10nl. I would imagine you didn't normalize to blinds by hand and just counted the gain and divided by bb and 100"

A diagnostic clue for the BB/100 investigation. The code actually does per-hand normalization correctly (`net_bb_won += player.net_won / big_blind` per hand), but the previous session's ad-hoc diagnostic scripts may have used a single fixed BB, producing misleading numbers that guided the investigation in the wrong direction.

## Important decisions made

- **Deferred BB/100 and all-in adjusted BB/100** from the sanity test. Both are commented out, not deleted. The ground truth values (13.1 and 7.74) remain in the test docstring.
- **Established a pattern**: get simple metrics green first, then tackle complex ones with dedicated focus time. The user explicitly plans to give Claude an extended session ("the entire night") to work through BB/100.

## Takeaways

- When an investigation stalls across multiple sessions, it's better to scope down and ship what works than to keep iterating in short bursts. The context loss between sessions makes complex debugging harder — each restart wastes time re-establishing state.
- Mixed-stakes data is a common source of normalization bugs. Always verify that per-hand normalization is happening, not aggregate division by a single blind value.
- The diagnostic scripts used during investigation can themselves have bugs that mislead the investigation. The "15.52 without cashout" number from the previous session was likely computed with a fixed BB, while the correct per-hand normalized value is 17.04.

## Next direction

The BB/100 investigation needs a dedicated deep session. Key facts established:
- Per-hand normalized BB/100 without cashout deduction: 17.04
- Per-hand normalized BB/100 with full cashout deduction: 10.67
- Expected (PT4 ground truth): 13.1
- There are 11 hands with cashout risk (not 7 as previously thought — some are opponent cashout, not Hero's)
- 2,752 hands at 5NL ($0.05 BB), 1,695 hands at 10NL ($0.10 BB)

The investigation should determine: (1) whether PT4 treats EV Cashout hands differently from regular hands in BB/100, and (2) whether the "Pays Cashout Risk" deduction should apply to Hero's net_won at all, or whether GGPoker's "collected" line already reflects the EV-adjusted amount for cashout hands.
