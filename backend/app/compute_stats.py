"""
Use case: compute stats for a player from persisted hands.

Reconstructs minimal domain Hand objects from DB rows, then delegates
to domain.stats.compute_stats (pure function, no DB dependency).
"""

import json
from datetime import datetime

from sqlalchemy.orm import Session

from db.schema import HandRow, PlayerRow
from domain.action import Action, ActionType
from domain.hand import GameType, Hand
from domain.player import Player
from domain.stats import PlayerStats, compute_stats as _domain_compute_stats
from domain.street import Street, StreetName


def compute_stats(player_name: str, *, session: Session) -> PlayerStats:
    hand_rows = (
        session.query(HandRow)
        .join(PlayerRow, PlayerRow.hand_id == HandRow.id)
        .filter(PlayerRow.name == player_name)
        .all()
    )
    hands = [_to_domain_hand(row) for row in hand_rows]
    return _domain_compute_stats(hands, player_name)


def _to_domain_hand(row: HandRow) -> Hand:
    players = [
        Player(name=p.name, seat=p.seat, stack=p.stack, net_won=p.net_won)
        for p in row.players
    ]
    streets = [
        Street(
            name=StreetName(s.name),
            cards=s.cards.split() if s.cards else [],
            actions=[
                Action(
                    player_name=a.player_name,
                    action_type=ActionType(a.action_type),
                    amount=a.amount,
                    is_all_in=a.is_all_in,
                )
                for a in sorted(s.actions, key=lambda x: x.action_order)
            ],
        )
        for s in sorted(row.streets, key=lambda x: x.street_order)
    ]
    all_in_equity = json.loads(row.allin_equity_json) if row.allin_equity_json else None

    return Hand(
        hand_id=row.hand_id,
        game_type=GameType(row.game_type),
        small_blind=row.small_blind,
        big_blind=row.big_blind,
        table_name=row.table_name,
        played_at=datetime.fromisoformat(row.played_at),
        players=players,
        streets=streets,
        hero_name=row.hero_name,
        is_walk=row.is_walk,
        pot=row.pot,
        rake=row.rake,
        cash_drop=row.cash_drop,
        all_in_equity=all_in_equity,
        all_in_pot_bb=row.allin_pot_bb,
    )
