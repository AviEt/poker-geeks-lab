# Adding Financial Columns to the Hands Table

## What I tried to accomplish

The hands table showed `net_won` but nothing else about the financial anatomy of each hand. The goal was to add enough columns to understand — at a glance — how much was in the pot, what rake was paid, the per-hand BB/100, and the adjusted version.

---

## How the session unfolded

The user opened with a clear list of five things to add to the hands table:

> BB/100, BB/100 adj, Pot won (not only net won), Rake in both $ and BB, Pot won after rake in $ and BB/100

Before writing a line of code, the TDD workflow required a test plan first. But writing the test plan surfaced an important ambiguity: what exactly is "pot won"? Is it what the player collected, or is it the gross pot before rake? And what does "pot won after rake" mean if the collected amount is already post-rake in PokerStars format?

The user stepped in with a precise three-line definition:

> 1. Net won — entire pot won minus rake, minus amount invested by hero
> 2. Pot won — entire pot won (including what hero put in), before deducting rake
> 3. Pot won after rake — entire pot won, w/o rake

And a critical edge case:

> In case hero's last action was raise and the villain(s) folded, the pot should not include the "return" part (the part hero bet beyond the initial call)

That last sentence was the key insight. In PokerStars format, the "Uncalled bet ($X) returned to Hero" line and the "Hero collected $Y from pot" line are separate. The "collected" amount is already the actual contested pot (not including what was returned). So `pot_won_after_rake` = sum of "collected" lines, and `pot_won` = collected + rake.

The uncalled bet must only credit `net_won`, not `pot_won_after_rake`. This distinction didn't exist in the codebase — both were merged into `net_won`.

---

## Key prompts that moved things forward

**The definitions prompt** was the turning point. Without the three-way distinction between net_won / pot_won / pot_won_after_rake, the implementation would have been ambiguous. The user's edge case about uncalled bets also directly dictated how `_apply_collected` needed to be split.

**The screenshot of the broken UI** — showing `Rake: $0.05` on a hand where hero lost — caught a real bug immediately after implementation: rake was always set to `hand.rake` regardless of whether the player won. The fix was one line: `hero_rake = rake if hero_won else 0.0`.

---

## Important decisions made

**`pot_won_after_rake` stored on `Player`, not derived at query time.** The parser is the only place that has access to the raw "collected" lines. By the time the API responds, all we have is aggregated numbers. The field needs to live in the domain and the DB.

**Both parsers updated in lockstep.** `pokerstars.py` and `ggpoker.py` both had their own `_apply_collected` method. The fix had to be applied to both — a reminder that shared logic between the two parsers isn't DRY yet.

**Rake is zero for losers.** Rake is a table-level cost, but from the perspective of per-hand reporting it only makes sense to attribute it to the player who won the pot. A losing hero paid their investment into the pot; the rake came out of the winner's collected amount.

**`_pot_stats()` helper introduced in the API route.** Rather than inlining 7 new fields directly in the `player_hands` dict comprehension, a small helper function was extracted. This keeps the route readable and groups the derived financial fields together.

**DB reset, not migration.** The new `pot_won_after_rake` column was added to the SQLAlchemy schema. Since this is SQLite in dev and `create_all` manages the schema, the right move was to kill the process, delete the `.db` file, and restart — not write a migration.

---

## Takeaways

**Column definitions need to be nailed before the test plan.** The initial test plan had to be revised once the user clarified the three-way distinction. That's fine — but it's a good reminder that financial stats require precise language up front. "Pot won" means different things to different people.

**Test the rake=0 case for losers separately.** It wasn't in the original test plan. A screenshot from the running app exposed it. Worth adding "what does this column show when hero lost?" to the standard checklist for any per-hand financial column.

**`getByText` breaks when two cells render identical values.** `bb_per_100` and `bb_per_100_adj` both rendered `300.00` in the test mock. `getByText('300.00')` threw "Found multiple elements." Fix: `getAllByText('300.00').length >= 1`. Design the mock data so values are unique when possible.

---

## Next direction

- BB/100 adj still uses actual result (not equity). Once all-in equity is parsed from hand histories, the adjusted column should diverge from BB/100 on all-in hands.
- The rake column currently uses the full hand rake when hero won the whole pot. For split pots (where hero wins a side pot but not the main), this will overstate rake. Worth a future fix once multi-winner hands are more common in the dataset.
- Consider adding positional breakdowns: BB/100 by position (BTN, CO, SB, etc.) as a follow-on stats feature.
