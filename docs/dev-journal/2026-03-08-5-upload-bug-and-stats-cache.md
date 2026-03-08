# Upload Bug Fix, Error Handling, and Stats Caching

## What I tried to accomplish

The user tried to upload hand histories and nothing happened — no error, no feedback, just silence. The session turned into a debugging investigation that uncovered a stale database schema, led to adding proper error handling in the frontend, and culminated in building an in-memory stats cache so the stats page loads instantly.

## How the session unfolded

The user reported the upload was broken with a simple "nothing happens." The first instinct was to trace the full upload flow from frontend to backend. The backend tests all passed (156 tests), the server was running, and the code looked correct on the surface. The breakthrough came from hitting the actual endpoint with curl — the response revealed the real error: `table hands has no column named allin_equity_json`.

The root cause was a schema drift. The `allin_equity_json` and `allin_pot_bb` columns had been added to the SQLAlchemy models in a previous session, but the SQLite database file on disk was created before those columns existed. SQLAlchemy's `create_all()` only creates missing tables — it doesn't alter existing ones. So every INSERT failed.

The reason the user saw "nothing" was a compounding problem: the backend returned errors inside a 200 response (in the `errors` array), and the frontend's `handleUpload` had a `try/finally` with no `catch` block. Errors were silently swallowed.

After fixing the upload, the user noticed the stats page was slow — showing skeleton cards for several seconds before loading. The stats were being recomputed from scratch on every page visit, querying all 4,447 hands and reconstructing domain objects each time. We discussed two approaches: in-memory cache vs. materialized DB table. The in-memory cache won for simplicity — no schema changes, no migrations, no triggers.

The cache implementation was straightforward but had a subtle testing issue. The lifespan event called `get_engine()` directly, which in tests would hit the real DB engine instead of the test override. This caused three pytest processes to spin at 100% CPU. The fix was to check `app.dependency_overrides` before calling the engine function.

Along the way, the user asked for a `/dev` slash command to manage start/stop/restart of both servers and database resets, which streamlined the rest of the session.

## Key prompts that moved things forward

> "Seems like there's a bug here - When I upload hands, nothing is loaded, nothing happens. Check the issue"

This kicked off the investigation. The vagueness of "nothing happens" was the key clue — it pointed to silent failure rather than a visible error.

> "You can drop the db completely and start it over"

The user cut through the investigation of the stale schema and gave a direct fix direction.

> "I want you to create a slash command for start/stop/restart backend/frontend/both and as well as for deleting the DB."

A workflow improvement that paid off immediately — the user used `/dev reset-db` and `/dev restart` multiple times in the same session.

> "Let's do option 1 but I want it: 1. Loaded upon app start 2. Recalculated and reloaded when new hands are imported. Bottom line - even first time going into this screen should be fast. There's no reason to wait never"

This refined the cache requirement beyond a simple lazy cache — the user wanted zero-latency on first visit, which meant warming the cache during the FastAPI lifespan startup event.

## Important decisions made

- **In-memory stats cache over materialized DB table.** The cache is warmed during FastAPI's lifespan startup and invalidated after every successful import. This avoids schema complexity while solving the performance problem. The tradeoff is that stats are lost on restart (but immediately recomputed from the DB on startup).

- **`/dev` slash command created.** Supports `start`, `stop`, `restart` with targets `be`/`fe`/`all`, plus `reset-db`. This removes the friction of manually killing processes, deleting DB files, and restarting servers.

- **Frontend error handling added.** `ImportPanel` now has a `catch` block that displays errors, and `importFiles()` checks `resp.ok` before parsing JSON. This prevents silent failures going forward.

- **Stats display formatting.** VPIP and PFR now use `.toFixed(2)` to show exactly two decimal places, matching BB/100 formatting.

## Takeaways

- Silent failures are the worst kind of bug. The combination of backend returning errors inside a 200 response and the frontend swallowing exceptions made this invisible. Always add error handling at the UI boundary.

- `Base.metadata.create_all()` is not a migration tool. It creates tables but never alters them. Any column additions require either a migration (Alembic) or a fresh DB.

- FastAPI's lifespan events interact with `dependency_overrides` — if the lifespan uses a dependency directly (not through `Depends`), tests will bypass the override. The fix is to check `app.dependency_overrides` explicitly.

- Having a `/dev` command for server management eliminated a lot of back-and-forth about "kill the process, delete the file, restart" sequences.

## Next direction

- Consider adding Alembic migrations so schema changes don't require dropping the database.
- The stats cache currently recomputes all players on every import — for larger datasets, incremental updates would be more efficient.
- The upload endpoint could benefit from progress feedback for large file batches.
