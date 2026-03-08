# E2E Sanity Test — Frozen

`backend/tests/test_e2e_sanity.py` is a **frozen production truth test**.

## Hard rules

- **Never modify this file** without explicit approval from the project owner.
- **Never run it automatically** — it is excluded from default pytest runs and must never be added to CI.
- **Never weaken or relax its assertions** — do not increase tolerances, add `.skip`, or comment out checks.
- **Never update the expected numbers** to make a failing test pass. If it fails, investigate the regression.

## What it tests

Imports all 32 real GGPoker hand history files from `tests/fixtures/hand_histories/real_hands/` and asserts exact aggregate stats for player `Hero`:

| Stat | Expected |
|---|---|
| Hands | 4447 |
| VPIP | 26.58% |
| PFR | 21.6% |
| BB/100 | 13.1 |
| All-in adj BB/100 | 7.74 |

## How to run

```
cd backend && uv run pytest -m sanity -v
```

Or via the run-tests skill: `/run-tests sanity`
