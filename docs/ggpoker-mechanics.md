# GGPoker Mechanics Affecting Winrate Calculations

## Rake Structure

- GGPoker takes rake on ALL streets, including preflop (unlike most sites that use no-flop-no-drop)
- Rake is taken even from 2-bet pots preflop
- Hand history summary line: `Total pot $X | Rake $Y | Jackpot $Z | Bingo $W | Fortune $V | Tax $U`
- Total fees = Rake + Jackpot + Bingo + Fortune + Tax
- Rake cap varies by stake and number of players in the hand

## EV Cashout Feature

### How it works
- Available only in cash games (not AoF)
- Triggers when: (1) players are all-in after the flop, and (2) a player has 60%+ equity
- Player sees an offer and must click quickly to accept
- If accepted, player receives their equity-based amount regardless of the hand outcome

### Cashout Formula
```
EV Cashout Amount = (Pot Size - Rake - Jackpot Fee) × Equity
```

### Fee
- 1% for Hold'em, PLO, PLO-5, Rush & Cash, Short Deck
- 2% for PLO-6

### Hand History Appearance
When the cashout player WINS the hand:
```
Hero: Chooses to EV Cashout
*** TURN *** [4h Qh 3s] [Jc]
*** RIVER *** [4h Qh 3s Jc] [7c]
Hero: Pays Cashout Risk ($1.85)
*** SHOWDOWN ***
Hero collected $8.86 from pot
```
- "Pays Cashout Risk" = player won the pot but pays back the excess over EV
- Net result: collected - cashout_risk = EV Cashout amount

When the cashout player LOSES the hand:
```
a69a2448: Receives Cashout ($1.14)
*** SHOWDOWN ***
opponent collected $X from pot
```
- "Receives Cashout" = player lost but receives the EV cashout payout
- Summary line shows: `won ($0) with ..., EV Cashout ($7.1)`

### Impact on Trackers
- PT4 treats cashout risk as a rake-like fee, NOT deducted from winrate
- For BB/100: cashout risk is excluded from net_won
- For All-in Adjusted BB/100: the equity formula replaces the actual result anyway

## Cash Drop (Promotional)

- GGPoker occasionally adds promotional cash to pots: `Cash Drop to Pot : total $X`
- This money is NOT invested by any player
- It IS part of the pot that the winner collects
- In hand histories: appears as a line in the preflop section

## Insurance (All-In Insurance)

- Separate from EV Cashout (older feature, similar concept)
- Not found in the test dataset hand histories
- Players can insure against specific outs after all-in

## Run It Multiple Times

- GGPoker does NOT appear to support run-it-twice in Rush & Cash (the format in our dataset)
- No "run it twice" patterns found in the 32 test hand history files
- If it exists in other formats, it would show as separate board runouts

## PokerTracker 4 All-In Equity Adjusted Formula

### The Formula
```
All-In Equity Adjusted = equity × (pot_after_rake) - player_investment
```

Where:
- `equity` = probability of winning calculated from known hole cards at the point of all-in
- `pot_after_rake` = total pot MINUS rake (and all fees)
- `player_investment` = total amount the player put into the pot

### Key Rules
1. **Rake IS subtracted** from pot before multiplying by equity
2. **All active players' cards must be known** — hands with unknown cards are excluded
3. **Ties are included** in equity calculation (split outcomes count as partial wins)
4. **Multi-way pots** with unknown cards are excluded entirely
5. **Players who fold after an all-in** are excluded (PT4 doesn't adjust when folding options remain)

### Example (from PT4 docs)
- Hero: AA, Villain: KK, both all-in for $100, pot = $200
- Hero equity: 82.6%
- Hero's equity in pot: $200 × 82.6% = $165.20
- All-in equity: $165.20 - $100 = **+$65.20**

### Sources
- [PT4 All-In Equity Graphs Guide](https://www.pokertracker.com/guides/PT4/tutorials/all-in-equity-graphs)
- [The Problem With All-In EV](https://www.pokertracker.com/blog/2011/10/the-problem-with-all-in-ev-all-in-equity)
- [PT4 Forum: All-in adjusted EV](https://www.pokertracker.com/forums/viewtopic.php?f=58&t=102881)
- [GGPoker EV Cashout](https://ggpoker.com/poker-games/ev-cashout/)
- [WorldPokerDeals EV Cashout Analysis](https://worldpokerdeals.com/blog/ev-cashout-at-ggpoker-everything-you-need-to-know)
