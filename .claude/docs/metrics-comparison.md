# Poker Metrics Comparison: PT4 / HM3 / H2N / PGL

Columns: PT4 = PokerTracker 4, HM3 = Holdem Manager 3, H2N = Hand2Note, PGL = this project.

**Effort** = T-shirt size to add the metric to PGL (✅ = done, XS < S < M < L < XL).

Sizing rationale:
- **✅** Already implemented
- **XS** Trivial — count/sum something already tracked, no new logic
- **S** Simple new calculation — clear definition, single-street or single-action logic
- **M** Moderate — requires spot identification (e.g. "who was preflop aggressor"), multi-action sequence within a street, or position-aware logic
- **L** Complex — multi-street dependency chains, conditional on prior street actions (e.g. float, probe)
- **XL** Requires major new infrastructure (e.g. equity calculation engine)

---

## General / Win Rate

| Metric | PT4 | HM3 | H2N | PGL | Effort |
|---|---|---|---|---|---|
| Hands Played | Hands | Hands | Hands | hands | ✅ |
| Win Rate (BB/100) | BB/100 | BB/100 | Win Rate | BB/100 | ✅ |
| Win Rate ($/100) | $/100 | Win Rate $ | N/A | dollar_per_100 | ✅ |
| All-in Adj. BB/100 | All-In Adj BB/100 | All-In Adjusted | N/A | BB/100 Adj | ✅ |
| Amount Won | Amount Won | Winnings | Winnings | amount_won | ✅ |
| Rake | Rake | Rake | N/A | N/A | M (rake must be parsed from hand histories) |
| Std Deviation | Std Dev | Std Dev | N/A | std_dev | ✅ |

## Preflop — General

| Metric | PT4 | HM3 | H2N | PGL | Effort |
|---|---|---|---|---|---|
| VPIP | VPIP | VPIP | VPIP | VPIP | ✅ |
| PFR | PFR | PFR | PFR | PFR | ✅ |
| RFI (Raise First In) | RFI | RFI | RFI | rfi | ✅ |
| Limp | LWPC | Limp | Limp | limp | ✅ |
| Limp-Call | N/A | Limp-Call | N/A | N/A | M |
| Limp-Raise | N/A | Limp-Raise | N/A | N/A | M |
| Call Open Raise | Called PFR | Call Open | Call Open Raise | call_open | ✅ |

## Preflop — 3Bet / 4Bet

| Metric | PT4 | HM3 | H2N | PGL | Effort |
|---|---|---|---|---|---|
| 3Bet Preflop | 3Bet Total | 3Bet | 3-Bet | three_bet | ✅ |
| 4Bet Preflop | 4Bet Total | 4Bet | 4-Bet | four_bet | ✅ |
| Fold to 3Bet | Fold to PF 3Bet | Fold to 3Bet | Fold to 3-Bet | fold_to_3bet | ✅ |
| Fold to 4Bet | Fold to PF 4Bet | Fold to 4Bet | N/A | fold_to_4bet | ✅ |
| Call 3Bet | Call PF 3Bet | Call 3Bet | N/A | call_3bet | ✅ |
| Squeeze | Squeeze | Squeeze | N/A | N/A | M (raiser + caller(s) already acted before you) |
| Fold to Squeeze | Fold to Squeeze | Fold to Squeeze | N/A | N/A | M |

## Preflop — Steal / Blinds

| Metric | PT4 | HM3 | H2N | PGL | Effort |
|---|---|---|---|---|---|
| Attempt to Steal | Att To Steal | Steal % | N/A | attempt_steal | ✅ |
| Fold BB to Steal | Fold BB to Steal | Fold BB to Steal | N/A | fold_bb_to_steal | ✅ |
| Fold SB to Steal | Fold SB to Steal | Fold SB to Steal | N/A | fold_sb_to_steal | ✅ |
| BB Defense vs Steal | N/A | BB Defense | N/A | N/A | S |
| SB Defense vs Steal | N/A | SB Defense | N/A | N/A | S |

## Postflop — General

| Metric | PT4 | HM3 | H2N | PGL | Effort |
|---|---|---|---|---|---|
| Saw Flop | Saw Flop % | Saw Flop | N/A | saw_flop | ✅ |
| Saw Turn | Saw Turn | Saw Turn | N/A | saw_turn | ✅ |
| Saw River | Saw River | Saw River | N/A | saw_river | ✅ |
| WWSF (Won When Saw Flop) | W$WSF | WWSF | WWSF | N/A | M (requires tracking pot winner per hand) |
| WTSD (Went to Showdown) | WTSD | WTSD | WTSD | wtsd | ✅ |
| W$SD (Won $ at Showdown) | W$SD | W$SD | W$SD | wsd | ✅ |

## Postflop — Aggression

| Metric | PT4 | HM3 | H2N | PGL | Effort |
|---|---|---|---|---|---|
| Aggression Factor (AF) | AF | Agg Factor | AF | N/A | M (bets+raises / calls across all streets) |
| Aggression Frequency (AFq) | AFq | Agg Pct | N/A | N/A | M |
| Flop AF | Flop AF | Flop Agg Factor | N/A | N/A | M |
| Turn AF | Turn AF | Turn Agg Factor | N/A | N/A | M |
| River AF | River AF | River Agg Factor | N/A | N/A | M |

## Postflop — C-Bet

| Metric | PT4 | HM3 | H2N | PGL | Effort |
|---|---|---|---|---|---|
| Flop C-Bet | CBet Flop | Flop CB | Continuation Bet Flop | N/A | M (must identify preflop aggressor, then check flop bet) |
| Turn C-Bet | CBet Turn | Turn CB | N/A | N/A | M |
| River C-Bet | CBet River | River CB | N/A | N/A | M |
| Fold to Flop C-Bet | Fold to F CBet | Fold to Flop CB | Fold to Continuation Bet Flop | N/A | M |
| Fold to Turn C-Bet | Fold to T CBet | Fold to Turn CB | N/A | N/A | M |
| Fold to River C-Bet | Fold to R CBet | Fold to River CB | N/A | N/A | M |
| Raise Flop C-Bet | Raise F CBet | Raise Flop CB | N/A | N/A | M |

## Postflop — Check-Raise

| Metric | PT4 | HM3 | H2N | PGL | Effort |
|---|---|---|---|---|---|
| Flop Check-Raise | Check Raise Flop | Flop Check Raise | N/A | N/A | M (check then raise on same street) |
| Turn Check-Raise | Check Raise Turn | Turn Check Raise | N/A | N/A | M |
| River Check-Raise | Check Raise River | River Check Raise | N/A | N/A | M |

## Postflop — Donk Bet

| Metric | PT4 | HM3 | H2N | PGL | Effort |
|---|---|---|---|---|---|
| Flop Donk Bet | Donk Flop | Donk Bet Flop | N/A | N/A | M (bet OOP into preflop aggressor) |
| Turn Donk Bet | Donk Turn | Donk Bet Turn | N/A | N/A | M |
| River Donk Bet | Donk River | Donk Bet River | N/A | N/A | M |
| Fold to Flop Donk Bet | Fold to F Donk | N/A | N/A | N/A | M |

## Postflop — Float / Probe

| Metric | PT4 | HM3 | H2N | PGL | Effort |
|---|---|---|---|---|---|
| Float Bet Turn | Float Turn | N/A | N/A | N/A | L (call flop IP → bet turn when checked to) |
| Float Bet River | Float River | N/A | N/A | N/A | L |
| Probe Bet | N/A | N/A | N/A | N/A | L (bet turn OOP after IP player checked back flop) |

## Position Stats

| Metric | PT4 | HM3 | H2N | PGL | Effort |
|---|---|---|---|---|---|
| VPIP by position (EP/MP/CO/BTN/SB/BB) | EP VPIP … BB VPIP | EP VPIP … BB VPIP | N/A | N/A | M (position already in domain model; needs position filter layer) |
| PFR by position | EP PFR … BB PFR | EP PFR … BB PFR | N/A | N/A | M |
| 3Bet by position | 3Bet EP … 3Bet BB | 3Bet EP … 3Bet BB | 3bet from MP … | N/A | M |

---

## PGL Coverage & Priorities

Currently implemented: **VPIP, PFR, BB/100, BB/100 All-in Adjusted, Hands Played, Amount Won, $/100, Saw Flop/Turn/River, RFI, Limp, Call Open, 3Bet, 4Bet, Fold to 3Bet, Fold to 4Bet, Call 3Bet, Attempt Steal, Fold BB/SB to Steal, WTSD, W$SD, Std Dev** (22 of ~60+ industry metrics).

Recommended implementation order (value vs effort):

| Priority | Metric | Effort | Notes |
|---|---|---|---|
| ✅ | XS + S metrics | — | Done |
| 1 | AF / AFq (overall + by street) | M | Core aggression metrics |
| 2 | Flop/Turn/River C-Bet + Fold to C-Bet | M | Most-used postflop stats; need PF aggressor tracking |
| 3 | WWSF | M | Completes the showdown triad |
| 4 | Check-Raise / Donk Bet | M | Common postflop reads |
| 5 | BB/SB Defense vs Steal | S | Complete the steal response picture |
| 6 | Squeeze / Fold to Squeeze | M | Complete the preflop betting tree |
| 7 | Position breakdowns (VPIP/PFR/3Bet by pos) | M | Unlocks position-aware profiling |
| 8 | Float / Probe | L | Advanced postflop; defer until core stats are done |

## Sources

- [PT3 Statistical Reference Guide](https://www.pokertracker.com/guides/PT3/general/statistical-reference-guide)
- [HM FAQ — Stat Definitions](https://faq.holdemmanager.com/questions/95/Stat+Definitions)
- [HM3 Situational Views](https://kb.holdemmanager.com/knowledge-base/article/situational-views)
- [Hand2Note — Key Preflop Stats](https://hand2note.com/Blog/Features/key-preflop-stats-player-profiling-and-basic-adjustments)
- [Hand2Note — Essential Postflop Stats](https://hand2note.com/Blog/Features/essential-postflop-stats)
- [Hand2Note Plain Stats Manual](http://hand2note3.hand2note.com/Help/pages/CustomStats/Plain/)
