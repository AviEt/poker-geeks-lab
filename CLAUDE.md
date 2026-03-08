# Poker Geeks Lab

## Rules (always apply)

@.claude/rules/architecture.md
@.claude/rules/tdd.md
@.claude/rules/poker-stats.md
@.claude/rules/design-system.md
@.claude/rules/e2e-sanity.md

## Quick Reference

**Run backend:** `cd backend && uv run uvicorn main:app --reload` → localhost:8000
**Run frontend:** `cd frontend && npm run dev` → localhost:5173
**Test backend:** `cd backend && uv run pytest`
**Test frontend:** `cd frontend && npm test`
**Design tokens:** `frontend/src/styles/tokens.css`

## Docs (load when relevant)

- [Architecture & module structure](.claude/docs/architecture.md)
- [Hand history file formats](.claude/docs/hand-history-files.md)
- [Design system details](.claude/docs/design-system.md)
