Implement a new poker statistic: $ARGUMENTS

## Step 1: Research (use subagent)
Launch a research subagent to web search how **PokerTracker4** defines and calculates this stat.
Also search Hold'em Manager and Hand2Note for cross-reference.
Collect: exact definition, formula, edge cases, street applicability.

## Step 2: Present findings + test plan
Present to the user:
1. **PT4 definition** — exact wording from the research
2. **Formula** — how to calculate it
3. **Edge cases** — walks, all-ins, missing streets, etc.
4. **Test plan** covering domain, API, and frontend layers

**Stop here and wait for user approval.** (TDD workflow per project rules applies.)

## Step 3: Implement per TDD rules
Follow the TDD workflow defined in the project rules.

## Step 4: Verify
Launch a test subagent to run all tests (backend + frontend).
Confirm: new tests pass AND no existing tests broken.

## Scaffolding conventions
- Stat logic: `backend/domain/stats.py` — add as a function
- Application: `backend/app/compute_stats.py` — update if needed
- API: add stat field to existing player stats response in `backend/api/routes/player_route.py`
- Frontend: display in `frontend/src/components/StatsPanel.tsx` using design tokens
- Use `var(--font-family-mono)` for stat values
