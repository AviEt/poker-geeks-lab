from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.import_route import router as import_router
from api.routes.player_route import router as player_router

app = FastAPI(title="Poker Geeks Lab", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_router)
app.include_router(player_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
