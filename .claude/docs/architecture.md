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
