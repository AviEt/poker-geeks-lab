from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_engine
from api.routes.import_route import router as import_router
from api.routes.player_route import router as player_router
from app.stats_cache import warm as warm_stats_cache


@asynccontextmanager
async def lifespan(application: FastAPI):  # noqa: ARG001
    engine_fn = app.dependency_overrides.get(get_engine, get_engine)
    warm_stats_cache(engine_fn())
    yield


app = FastAPI(title="Poker Geeks Lab", version="0.1.0", lifespan=lifespan)

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
