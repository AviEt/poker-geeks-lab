# Poker Geeks Lab — Project Rules

These rules apply to every task in this project, every session, without exception.

## Architecture

- **UI is a pure presentation layer.** Zero business logic in the frontend.
  Every user action goes through the API. The React app only renders data and calls endpoints.
- **Layered architecture** with strict downward dependency flow:
  `Frontend → API (FastAPI) → Application → Domain → Infrastructure`
- **Domain layer has zero external dependencies** (no DB, no I/O, no HTTP).

## Code Style

- **One model per file.** Each domain entity lives in its own file.
  e.g. `domain/hand.py`, `domain/player.py`, `domain/action.py`, `domain/street.py`

## TDD Workflow (mandatory for every new feature)

1. Present a **high-level test plan in plain English**
2. Wait for **user approval**
3. Write the tests (they must fail at this point)
4. Implement until all tests pass without breaking any existing tests

Never skip this workflow. Never write implementation before tests are approved.

## Poker Statistics

- Before implementing any poker statistic, **do a web search** on how
  **PokerTracker4**, **Hold'em Manager (HM2/HM3)**, and **Hand2Note (H2N)**
  define and calculate it.
- Use their definitions as the **source of truth**.
- Always look up poker and poker analysis terminology in **PokerTracker4**
  before using terms in code, comments, or docs.

## Hand History Files

- Example hand history files live in `backend/tests/fixtures/hand_histories/`
- Real hand samples live in `backend/tests/fixtures/hand_histories/real_hands/`
- GGPoker files contain **multiple hands per file** (separated by blank lines)
- PokerStars files contain one hand per file

## Tech Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Backend   | Python 3.12, FastAPI              |
| Database  | PostgreSQL, SQLAlchemy 2, Alembic |
| Frontend  | React + Vite (TypeScript)         |
| Testing   | pytest (backend), Vitest (frontend) |
| Packaging | uv (Python), npm (frontend)       |

## Running the Project

```bash
# Backend
cd backend
uv run uvicorn main:app --reload   # starts on http://localhost:8000

# Frontend
cd frontend
npm run dev                         # starts on http://localhost:5173

# Tests
cd backend
uv run pytest
```
