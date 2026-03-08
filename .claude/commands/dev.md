Manage dev servers and database.

**Argument:** $ARGUMENTS

## Command parsing
Parse the argument as `<action> [target]`:

**Actions:** `start`, `stop`, `restart`, `reset-db`
**Targets:** `be` or `backend`, `fe` or `frontend`, `all` or empty (both)

`reset-db` ignores the target — it always operates on the backend database.

Examples: `start be`, `restart`, `stop fe`, `reset-db`

## Server management

**Backend start:**
```
cd backend && uv run uvicorn main:app --reload
```
Run in background. Verify with `curl -s http://localhost:8000/health` after a 2s delay.

**Frontend start:**
```
cd frontend && npm run dev
```
Run in background.

**Stop:** Find processes on the relevant ports and kill them.
- Backend: port 8000 (`lsof -i :8000 -t | xargs kill`)
- Frontend: port 5173 (`lsof -i :5173 -t | xargs kill`)

**Restart:** Stop then start.

When target is `all` or empty, operate on both backend and frontend in parallel.

## Database reset (`reset-db`)

1. Stop the backend (kill port 8000)
2. Delete `backend/poker_geeks_lab.db`
3. Start the backend (so the DB is recreated with the current schema)
4. Confirm the health endpoint responds

## Reporting
After each action, report:
- What was done
- Whether services are running (check ports)
- For `reset-db`: confirm DB was recreated
