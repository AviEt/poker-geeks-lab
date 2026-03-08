# Architecture Rules

- **UI is a pure presentation layer.** Zero business logic in the frontend. Every user action goes through the API — the React app only renders data and calls endpoints.
- **Strict layered architecture** with downward-only dependency flow: `Frontend → API → Application → Domain → Infrastructure`
- **Domain layer has zero external dependencies** — no DB, no I/O, no HTTP.

See [architecture.md](../docs/architecture.md) for the full module structure.
