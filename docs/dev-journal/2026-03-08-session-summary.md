# Session Summary — Full Project Build (Inception to MVP+)

## Context

This journal covers the entire project from scratch. The goal is **Poker Geeks Lab** — a local poker learning system that starts as a hand tracker and will evolve into a training platform.

The project was built in a single long Claude Code session (with context compaction mid-way). It started with zero code and ended with a fully working app: import GGPoker/PokerStars hand history files, view VPIP/PFR/BB stats, browse hands table with position/cards/board, and click into a visual per-hand detail view.

---

## Key Prompts

### Architecture & Setup
1. **"New project from scratch. Goal: poker learning system starting as a hand tracker"**
   → Produced the full architecture plan, tech stack, module structure, and iteration roadmap.

2. **"What would you use to avoid duplications? I would also like a test that makes sure that the N hands persisted is consistent with the number of hands in the file"**
   → Introduced UNIQUE constraint on `hand_id` + `IntegrityError` catch for idempotent imports, plus a parser-count consistency test.

3. **"I suggest to support endpoints for player: GET /{player}/stats and GET /{player}/hands — WDYT?"**
   → Adopted player-centric URL structure over resource-centric `/stats/{player}`.

### UI
4. **"Let's do UI"** → React+Vite frontend with ImportPanel, StatsPanel, HandsTable.

5. **"I see a blank screen"** + error `The requested module '/src/api/client.ts' does not provide an export named 'ImportResult'`
   → Root cause: Vite's module transform doesn't export TypeScript interfaces at runtime. Fix: `import type { X }` for all type-only imports.

### Hand Table & Detail View
6. **"In the main table add columns: a) Hole Cards b) Flop c) Turn d) River e) position (of hero) — make it actually in the beginning"**
   → Extended `GET /{player}/hands` response; updated HandsTable columns.

7. **"I want to be able to click a hand and see the entire action in easily human readable form. Take inspiration from this image"** *(poker app screenshot)*
   → Built HandDetail component with tabbed streets and action timeline.

8. **"Try to make the hand visual like in this image when you go into a specific hand"**
   → Full visual redesign: dark theme, player strip with avatars, visual card rectangles, colored action badges, showdown section.

9. **"The position appears unknown in the table — fix it"**
   → Diagnosed stale DB (imported before `assign_positions` was wired). Deleted DB, user re-imported.

10. **"In the single hand view I would like to see the hero's hole cards and also the villain's in the end of the action if there was a showdown"**
    → Added `CardPair` visual component and Showdown section.

11. **"Yes, I would like to also both unit-test and integration tests. But you can wait with the integration tests. When we get there I'll dump you the PT4 DB and you'll use it as mock"**
    → Deferred integration tests; noted for future phase.

---

## Main Outputs

### Phase 1 — Architecture & Domain Models

**Project rules established (in CLAUDE.md):**
- UI is pure presentation — all logic via API
- One model per file
- TDD workflow: test plan → approval → tests → implement
- Stats must be researched from PT4/HM/H2N before implementing
- Strict downward dependency flow: Frontend → API → Application → Domain → Infrastructure

**Domain models (zero external dependencies):**

| File | Contents |
|------|----------|
| `domain/hand.py` | `Hand` dataclass, `GameType` enum |
| `domain/player.py` | `Player` dataclass, `Position` enum (SB/BB/UTG/HJ/CO/BTN/etc.), `assign_positions()` |
| `domain/action.py` | `Action` dataclass, `ActionType` enum (fold/check/call/bet/raise/post_sb/post_bb/post_ante/shows/mucks/wins) |
| `domain/street.py` | `Street` dataclass, `StreetName` enum (preflop/flop/turn/river) |
| `domain/stats.py` | `compute_stats()` — pure Python, no DB/IO |

**Stats computed (researched from PT4/HM/H2N):**
- VPIP: voluntary money put in preflop (call or raise, not blind posts)
- PFR: raised preflop
- BB/100: net chips won per 100 hands in big blinds
- BB/100 adjusted: replaces all-in equity spot results with EV (future — left as alias for now)

### Phase 2 — Parsers

**`parsers/base.py`** — `BaseParser` ABC + `ParseError`

**`parsers/pokerstars.py`** — PokerStars hand history parser
- One hand per `.txt` file
- Regex-based: header, blinds, seats, hole cards, streets, showdown, summary
- Parses: hand_id, played_at, table_name, blinds, players+stacks, positions (from button seat), hole cards, all actions, board cards, pot, rake
- `_apply_collected` / `_apply_invested` for net_won calculation (RAISE amounts are total-to, not delta)
- Walk detection (everyone folds to BB)
- Uncalled bets credited back

**`parsers/ggpoker.py`** — GGPoker hand history parser
- Multiple hands per file (separated by blank lines), split via `_HAND_START` regex
- Differences from PokerStars: `SHOWDOWN` vs `SHOW DOWN`, shows appear in action sections, `Dealt to` for opponents has no cards, rake line has extra fee fields (Jackpot/Bingo/Fortune/Tax)
- Cash Drop to Pot: GGPoker promotional money — tracked separately, excluded from net_won calculations
- Conservation law enforced in tests: `sum(net_won) == cash_drop - rake`

### Phase 3 — Database Layer

**`db/schema.py`** — SQLAlchemy 2 ORM

```
hands     → one row per hand
players   → one row per player per hand  (UNIQUE on hand_id + name)
streets   → one row per street per hand  (ordered by street_order)
actions   → one row per action per street (ordered by action_order)
```

Key decisions:
- `played_at` stored as ISO-8601 string (not DateTime) to avoid timezone complexity
- `hole_cards` stored as space-separated string (`"As Kh"`)
- `position` stored as string value of the enum (e.g. `"BTN"`)
- Cascade delete from hand → players/streets → actions

**`db/repository.py`** — `HandRepository`
- `save_hand(hand)` — idempotent; catches `IntegrityError` on duplicate `hand_id`, returns `None` for skips
- `get_hand(hand_id)` — lookup by hand_id string

### Phase 4 — Application Layer

**`app/import_hands.py`** — `import_hands(path, *, engine)`
- Auto-detects GGPoker vs PokerStars by checking for `"Poker Hand #RC"` in file
- Returns `{"imported": N, "skipped": M, "errors": [...]}`

**`app/compute_stats.py`** — `compute_stats(player, *, session)`
- Queries hands + players from DB, reconstructs domain `Hand` objects, delegates to `domain.stats.compute_stats()`

### Phase 5 — API Layer

**`api/deps.py`** — FastAPI dependency injection
```python
def get_engine() -> Engine  # overridden in tests with StaticPool SQLite
def get_session(engine) -> Session
```

**Endpoints:**

| Endpoint | Description |
|----------|-------------|
| `POST /import` | Upload one or more `.txt` files; returns `{imported, skipped, errors}` |
| `GET /{player}/stats` | VPIP, PFR, BB/100, BB/100 adjusted, hands count |
| `GET /{player}/hands` | Paginated hand list (page, page_size ≤500); includes hero_position, hero_hole_cards, flop, turn, river, net_won |
| `GET /{player}/hands/{hand_id}` | Full hand detail: players, streets with actions, pot, rake. 404 if hand or player not found |

### Phase 6 — Frontend

**Tech:** React + Vite + TypeScript. Pure presentation — zero business logic.

**`api/client.ts`** — typed fetch wrappers for all 4 endpoints + full TypeScript interfaces (`ImportResult`, `PlayerStats`, `HandSummary`, `HandsResponse`, `HandDetail`, `HandPlayer`, `HandStreet`, `HandAction`).

**Components:**

| Component | Description |
|-----------|-------------|
| `ImportPanel.tsx` | File input (multiple `.txt`), Upload button, shows imported/skipped/errors |
| `StatsPanel.tsx` | Displays VPIP, PFR, BB/100, BB/100 adj for a player |
| `HandsTable.tsx` | Paginated table; columns: Position, Hand ID, Hole Cards, Flop, Turn, River, Net Won, Stakes, Date; rows are clickable |
| `HandDetail.tsx` | Visual hand detail: player strip with avatars+cards, board card rectangles, pot, tabbed street navigation, action timeline with colored badges, showdown section |
| `HandDetail.css` | BEM CSS, dark theme (`#1a1f2e` background), card visuals |

**`App.tsx`** — `refreshKey` pattern to re-mount StatsPanel after import; `selectedHandId` state to switch between HandsTable and HandDetail.

### Phase 7 — Testing

**Backend (132 tests):**
- `test_parser_ggpoker.py` — 78 tests: header, seats, positions, streets, actions, net_won conservation, walk detection, cash drop, multi-hand files
- `test_db.py` — 23 tests: schema, repo save/skip/idempotency, import use case
- `test_api.py` — 31 tests: import endpoint, stats endpoint, hands list (including extended fields), hand detail (200, fields, actions, 404s)

**Frontend (29 tests):**
- `ImportPanel.test.tsx` — 6 tests
- `StatsPanel.test.tsx` — 6 tests
- `HandsTable.test.tsx` — 9 tests (including new columns + click handler)
- `HandDetail.test.tsx` — 7 tests (fetch, tabs, action display, showdown, close)

---

## Plan Feedback

| Moment | User Feedback |
|--------|--------------|
| Deduplication approach | User raised the question first; approved UNIQUE + IntegrityError approach |
| URL structure | User proposed player-centric `/{player}/stats` over `/stats/{player}` — adopted |
| Integration tests | Deferred; user will provide PT4 DB dump when ready |
| All TDD plans | User approved each test plan with "Yes" / "Proceed" before implementation |
| Position "UNKNOWN" bug | User correctly identified the issue in the UI; confirmed DB deletion as the fix |
| Visual hand detail | Two iterations: first plain list, then full visual redesign based on a screenshot the user shared |

---

## Claude Code Configuration Changes

- **`CLAUDE.md`** — Project rules file checked into the repo:
  - Pure presentation UI, one model per file, TDD workflow, stats from PT4/HM/H2N, hand history fixture paths
- **`.claude/commands/journal.md`** — Custom `/journal` slash command added by user at end of session

---

## Code / Architecture Changes

### Complete file inventory

**Backend:**
```
backend/
├── parsers/
│   ├── base.py
│   ├── pokerstars.py
│   └── ggpoker.py
├── domain/
│   ├── hand.py
│   ├── player.py
│   ├── action.py
│   ├── street.py
│   └── stats.py
├── db/
│   ├── schema.py
│   └── repository.py
├── app/
│   ├── import_hands.py
│   └── compute_stats.py
├── api/
│   ├── deps.py
│   └── routes/
│       ├── import_route.py
│       └── player_route.py
├── main.py
└── tests/
    ├── fixtures/hand_histories/real_hands/   ← real GGPoker files
    ├── test_parser_ggpoker.py
    ├── test_db.py
    └── test_api.py
```

**Frontend:**
```
frontend/src/
├── api/client.ts
├── components/
│   ├── ImportPanel.tsx
│   ├── StatsPanel.tsx
│   ├── HandsTable.tsx
│   ├── HandDetail.tsx
│   └── HandDetail.css
├── __tests__/
│   ├── ImportPanel.test.tsx
│   ├── StatsPanel.test.tsx
│   ├── HandsTable.test.tsx
│   └── HandDetail.test.tsx
├── App.tsx
└── main.tsx
```

### Key architectural decisions

**1. Strict layer separation**
Domain has zero external dependencies. Stats logic lives entirely in `domain/stats.py` as pure Python functions taking `Hand` objects. No SQLAlchemy, no FastAPI imports anywhere in the domain layer.

**2. Idempotent imports via UNIQUE constraint**
`hands.hand_id` has a DB-level UNIQUE constraint. On re-import, `IntegrityError` is caught and the hand is silently skipped. This is safer than application-level "check before insert" which has a race condition.

**3. StaticPool for test isolation**
FastAPI tests override `get_engine` with a `StaticPool` SQLite in-memory engine. This ensures all sessions within a test share the same in-memory DB (avoids the problem where each new `Session` opens a new connection to a different in-memory DB).

**4. Player-centric URLs**
`GET /{player}/stats` and `GET /{player}/hands` instead of `/stats/{player}`. More natural for a per-player hand tracking tool. Consistent with how tools like PT4 organize data.

**5. RAISE amounts are total-to, not delta**
In both PokerStars and GGPoker format, `raises $X to $Y` means $Y total invested on the street, not $X additional. `_apply_invested` replaces (not adds) the invested amount when a RAISE is seen.

**6. Eager loading to avoid N+1**
`GET /{player}/hands` uses `joinedload(HandRow.players)` and `joinedload(HandRow.streets)` on the paginated query. Applied after `.offset()/.limit()` to avoid inflating row counts.

**7. `import type { X }` in all frontend components**
Vite's module transform does not export TypeScript interfaces at runtime. Using `import type { X }` for interface imports prevents a blank-screen crash.

**8. DB deletion over migration for stale positions**
`assign_positions()` was added to parsers after initial hands were already imported. Positions were all "UNKNOWN" in the DB. For local SQLite dev, deleting the DB and re-importing is the right call. For production PostgreSQL, an Alembic migration with a backfill query would be needed.

---

## Bugs Fixed

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| `python-multipart` not installed | FastAPI requires it for `UploadFile` | `uv add python-multipart` |
| Import endpoint returned 0 imported | `session.get_bind()` in import route used separate SQLite connections | `StaticPool` engine injected via `Depends(get_engine)` |
| `page_size=10000` test failed | Route has `le=500` validation | Changed test to use `page_size=500` |
| Duplicate React keys in pagination test | `Array(20).fill(HAND)` creates 20 identical hand_ids | `Array.from({ length: 20 }, (_, i) => ({ ...HAND, hand_id: \`p1-${i}\` }))` |
| `5.10` renders as `5.1` | JS drops trailing zeros from numbers | `.toFixed(2)` in StatsPanel |
| Blank screen on frontend | Vite module transform doesn't export TS interfaces | `import type { X }` for all type-only imports |
| Missing `App.css` import | Lost during App.tsx rewrite | Re-added `import './App.css'` |
| Positions all "UNKNOWN" in DB | Hands imported before `assign_positions()` was wired | Deleted SQLite DB, re-imported files |
| `getByText('Hero')` fails | Multiple elements with same text in visual component | `getAllByText('Hero').length > 0` |

---

## Lessons Learned

1. **Wire derived logic before first import.** Positions were correct in the parser but the DB had stale data. Always check DB consistency when adding new derived fields to existing import pipelines.

2. **`import type` is mandatory for Vite + TypeScript.** Non-value imports (`interface`, `type`) must use `import type { X }` or they cause a runtime crash in Vite's module transform.

3. **StaticPool is the correct SQLite test pattern for FastAPI.** Without it, each `Session()` opens a new connection to a fresh in-memory DB, making all data invisible across dependency injection boundaries.

4. **RAISE amounts are totals, not deltas.** `"raises $0.50 to $1.00"` means $1.00 total invested this street, not $0.50 more. Getting this wrong produces incorrect net_won calculations.

5. **`getByText` breaks in visual components with repeated names.** When a name appears in player chips, action items, and showdown sections simultaneously, use `getAllByText(...).length > 0`.

6. **Conservation law as test oracle.** For net_won correctness: `sum(net_won for all players) == cash_drop - rake`. This is a deterministic constraint that doesn't require hand-by-hand manual calculation.

7. **Player-centric URL design.** For per-player stats tools, `/{player}/stats` reads more naturally than `/stats/{player}` and makes it trivial to add more player-scoped endpoints later.

---

## Next Steps

- **Richer stats:** 3-bet%, AF, CBet%, positional breakdown — research PT4/HM/H2N definitions first
- **Integration tests:** User will provide PT4 DB dump; use it to validate parser + stats output against known-correct values
- **Free-text hand querying:** Natural language → SQL via Text2SQL model
- **GGPoker edge cases:** All-in equity hands, ante-only posts, tournament formats
- **Hand replay:** Animate street-by-street with pot progression
- **PostgreSQL migration:** Replace SQLite with PostgreSQL for production; add Alembic backfill migration for positions
- **Cloud deployment + auth layer**
- **PokerStars parser:** Validate against real PokerStars files (currently tested against GGPoker)
