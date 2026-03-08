# Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Python 3.12, FastAPI                |
| Database  | PostgreSQL, SQLAlchemy 2, Alembic   |
| Frontend  | React + Vite (TypeScript), Tailwind CSS v4, Geist font |
| Testing   | pytest (backend), Vitest (frontend) |
| Packaging | uv (Python), npm (frontend)         |

## Running the Project

```bash
# Backend
cd backend
uv run uvicorn main:app --reload   # http://localhost:8000

# Frontend
cd frontend
npm run dev                         # http://localhost:5173

# Tests
cd backend
uv run pytest
```
