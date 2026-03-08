# Architecture

Strict layered architecture with downward-only dependency flow:

```
Frontend → API (FastAPI) → Application → Domain → Infrastructure
```

- **Frontend** — pure presentation layer, no business logic; every user action calls the API
- **API** — FastAPI; all logic exposed as REST endpoints
- **Application** — use cases, orchestrates domain and infrastructure
- **Domain** — pure Python dataclasses and logic; zero external dependencies (no DB, no I/O, no HTTP)
- **Infrastructure** — DB, parsers, file I/O

## Database Migrations (Alembic)

Schema changes are managed via Alembic. Migrations run automatically on every backend startup (`alembic upgrade head` is called in the FastAPI lifespan before the app is ready).

**Adding a new column or table:**
1. Edit `db/schema.py`
2. From `backend/`, run: `uv run alembic revision --autogenerate -m "describe_change"`
3. Review the generated file in `db/migrations/versions/`
4. Next restart applies it automatically

**Manual migration commands** (run from `backend/`):
```
uv run alembic upgrade head       # apply all pending migrations
uv run alembic current            # show current revision
uv run alembic history            # list all revisions
uv run alembic downgrade -1       # roll back one revision
```

> `render_as_batch=True` is set in `env.py` for SQLite compatibility (required for ALTER TABLE operations).

## Module Structure

```
poker_geeks_lab/
├── backend/
│   ├── parsers/         # base.py, pokerstars.py, ggpoker.py
│   ├── domain/          # hand.py, player.py, action.py, street.py, stats.py
│   ├── db/              # schema.py, repository.py, migrations/
│   ├── app/             # import_hands.py, compute_stats.py
│   ├── api/routes/
│   └── tests/fixtures/hand_histories/
└── frontend/
    ├── src/
    │   ├── styles/tokens.css    # design tokens (single source of truth)
    │   ├── components/          # React components (each has a .tsx + .css)
    │   └── api/client.ts        # API fetch functions
    └── public/fonts/            # Geist variable font files
```
