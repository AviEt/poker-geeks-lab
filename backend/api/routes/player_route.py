"""
GET /{player}/stats          — VPIP, PFR, BB/100, BB/100 adjusted for a player
GET /{player}/hands          — paginated hand list for a player
GET /{player}/hands/{hand_id} — full hand detail (streets + actions)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from api.deps import get_session
from app.compute_stats import compute_stats
from db.schema import ActionRow, HandRow, PlayerRow, StreetRow

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
    rows = (
        query
        .options(joinedload(HandRow.players), joinedload(HandRow.streets))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    hands = []
    for row in rows:
        hero_player = next((p for p in row.players if p.name == player), None)
        board = _extract_board(row.streets)
        hands.append({
            "hand_id": row.hand_id,
            "played_at": row.played_at,
            "table_name": row.table_name,
            "game_type": row.game_type,
            "small_blind": row.small_blind,
            "big_blind": row.big_blind,
            "hero_name": row.hero_name,
            "hero_position": hero_player.position if hero_player else None,
            "hero_hole_cards": hero_player.hole_cards if hero_player else None,
            "flop": board.get("flop"),
            "turn": board.get("turn"),
            "river": board.get("river"),
            "net_won": hero_player.net_won if hero_player else 0.0,
        })

    return {"player": player, "total": total, "page": page, "page_size": page_size, "hands": hands}


@router.get("/{player}/hands/{hand_id}")
def hand_detail(
    player: str,
    hand_id: str,
    session: Session = Depends(get_session),
) -> dict:
    row = (
        session.query(HandRow)
        .filter(HandRow.hand_id == hand_id)
        .options(
            joinedload(HandRow.players),
            joinedload(HandRow.streets).joinedload(StreetRow.actions),
        )
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Hand {hand_id} not found")

    hero_player = next((p for p in row.players if p.name == player), None)
    if hero_player is None:
        raise HTTPException(status_code=404, detail=f"Player {player} not in hand {hand_id}")

    players = [
        {
            "name": p.name,
            "seat": p.seat,
            "stack": p.stack,
            "position": p.position,
            "hole_cards": p.hole_cards,
            "net_won": p.net_won,
        }
        for p in row.players
    ]

    streets = []
    for street in sorted(row.streets, key=lambda s: s.street_order):
        actions = [
            {
                "player": a.player_name,
                "action": a.action_type,
                "amount": a.amount,
                "is_all_in": a.is_all_in,
            }
            for a in sorted(street.actions, key=lambda a: a.action_order)
        ]
        streets.append({
            "name": street.name,
            "cards": street.cards,
            "actions": actions,
        })

    return {
        "hand_id": row.hand_id,
        "played_at": row.played_at,
        "table_name": row.table_name,
        "game_type": row.game_type,
        "small_blind": row.small_blind,
        "big_blind": row.big_blind,
        "pot": row.pot,
        "rake": row.rake,
        "hero_name": row.hero_name,
        "players": players,
        "streets": streets,
    }


def _extract_board(streets: list) -> dict[str, str | None]:
    board: dict[str, str | None] = {}
    for s in streets:
        if s.name in ("flop", "turn", "river") and s.cards:
            board[s.name] = s.cards
    return board
