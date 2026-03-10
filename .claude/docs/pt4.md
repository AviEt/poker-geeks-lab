# PokerTracker 4 (PT4) — Ground Truth Reference

PT4 is the authoritative source of truth for all poker statistics definitions and calculations.

## Database Access

PT4 uses PostgreSQL. Connect with:

- **Host:** localhost
- **Port:** 5432
- **User:** postgres
- **Password:** dbpass
- **Database:** `PT4_2026_03_08_155912` (the reference DB — contains the same ~4447 hands as our test fixtures)

> All other databases in this PostgreSQL instance are **out of scope**.

```bash
psql -U postgres -h localhost -d PT4_2026_03_08_155912
```

## Cross-Referencing Workflow

When asked to "cross-reference with PT4":

1. Connect to the PT4 PostgreSQL database
2. Query the relevant stats/hands for the player in question
3. Compare against our computed values
4. Investigate any discrepancies

## Key Tables (PT4 schema)

Common tables in `PT4_2026_03_08_155912`:

- `player` — player records
- `hand_history` — individual hands
- `cash_hand_player_statistics` — per-hand stats per player (VPIP, PFR, etc.)
- `cash_hand_summary` — hand-level summaries

List tables:
```bash
psql -U postgres -h localhost -d PT4_2026_03_08_155912 -c "\dt"
```
