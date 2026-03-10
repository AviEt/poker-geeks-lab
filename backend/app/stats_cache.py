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
        "amount_won": round(stats.amount_won, 4),
        "dollar_per_100": round(stats.dollar_per_100, 4),
        "saw_flop": round(stats.saw_flop.percentage, 4),
        "saw_turn": round(stats.saw_turn.percentage, 4),
        "saw_river": round(stats.saw_river.percentage, 4),
        "rfi": round(stats.rfi.percentage, 4),
        "limp": round(stats.limp.percentage, 4),
        "call_open": round(stats.call_open.percentage, 4),
        "three_bet": round(stats.three_bet.percentage, 4),
        "four_bet": round(stats.four_bet.percentage, 4),
        "fold_to_3bet": round(stats.fold_to_3bet.percentage, 4),
        "fold_to_4bet": round(stats.fold_to_4bet.percentage, 4),
        "call_3bet": round(stats.call_3bet.percentage, 4),
        "attempt_steal": round(stats.attempt_steal.percentage, 4),
        "fold_bb_to_steal": round(stats.fold_bb_to_steal.percentage, 4),
        "fold_sb_to_steal": round(stats.fold_sb_to_steal.percentage, 4),
        "wtsd": round(stats.wtsd.percentage, 4),
        "wsd": round(stats.wsd.percentage, 4),
        "std_dev": round(stats.std_dev, 4),
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
