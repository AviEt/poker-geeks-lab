"""
In-memory stats cache.

Warmed on app startup, refreshed after each import.
Keyed by player name.
"""

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.compute_stats import compute_stats
from db.schema import PlayerRow
from domain.stats import PlayerStats

_cache: dict[str, dict] = {}


def _serialize(player: str, stats: PlayerStats) -> dict:
    return {
        "player": player,
        "hands": stats.hands,
        "vpip": round(stats.vpip.percentage, 4),
        "pfr": round(stats.pfr.percentage, 4),
        "bb_per_100": round(stats.bb_per_100, 2),
        "bb_per_100_adjusted": round(stats.bb_per_100_adjusted, 2),
    }


def warm(engine: Engine) -> None:
    """Compute and cache stats for every player in the DB."""
    with Session(engine) as session:
        players = [row[0] for row in session.query(PlayerRow.name).distinct()]
        for player in players:
            stats = compute_stats(player, session=session)
            _cache[player] = _serialize(player, stats)


def invalidate(engine: Engine) -> None:
    """Recompute all cached stats (call after import)."""
    warm(engine)


def get(player: str) -> dict | None:
    """Return cached stats for a player, or None if not cached."""
    return _cache.get(player)
