"""
GET /{player}/stats  — VPIP, PFR, BB/100, BB/100 adjusted for a player
GET /{player}/hands  — paginated hand list for a player
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_session
from app.compute_stats import compute_stats
from db.schema import HandRow, PlayerRow

router = APIRouter()


@router.get("/{player}/stats")
def player_stats(player: str, session: Session = Depends(get_session)) -> dict:
    stats = compute_stats(player, session=session)
    return {
        "player": player,
        "hands": stats.hands,
        "vpip": round(stats.vpip.percentage, 1),
        "pfr": round(stats.pfr.percentage, 1),
        "bb_per_100": round(stats.bb_per_100, 2),
        "bb_per_100_adjusted": round(stats.bb_per_100_adjusted, 2),
    }


@router.get("/{player}/hands")
def player_hands(
    player: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    session: Session = Depends(get_session),
) -> dict:
    query = (
        session.query(HandRow)
        .join(PlayerRow, PlayerRow.hand_id == HandRow.id)
        .filter(PlayerRow.name == player)
        .order_by(HandRow.played_at.desc())
    )
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    hands = [
        {
            "hand_id": row.hand_id,
            "played_at": row.played_at,
            "table_name": row.table_name,
            "game_type": row.game_type,
            "small_blind": row.small_blind,
            "big_blind": row.big_blind,
            "hero_name": row.hero_name,
        }
        for row in rows
    ]

    return {"player": player, "total": total, "page": page, "page_size": page_size, "hands": hands}
