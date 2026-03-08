Run project tests and report results.

**Argument:** $ARGUMENTS

## Scope selection
Parse the argument to determine which tests to run:
- `be` or `backend` → backend only
- `fe` or `frontend` → frontend only
- `all` or empty → both backend and frontend
- `sanity` → backend e2e sanity test only (see `.claude/rules/e2e-sanity.md`)
- Any other value → treat as a pytest/vitest filter (e.g., `test_stats`, `StatsPanel`)

## Execution
Launch subagents (in parallel when running both):

**Backend:**
```
cd backend && uv run pytest -v [filter if provided]
```

**Sanity (scope = `sanity`):**
```
cd backend && uv run pytest -m sanity -v
```

**Frontend:**
```
cd frontend && npm test -- --run [filter if provided]
```

## Reporting
Present a unified summary:
1. **Scope:** what was run
2. **Results:** pass/fail count per suite, list any failures with file + test name
3. **Verdict:** all green, or list what needs fixing

If there are failures, read the failing test files and relevant source to diagnose root causes. Present a fix plan — do NOT auto-fix unless the user asks.
