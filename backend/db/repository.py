"""
Data access layer.

HandRepository persists domain Hand objects and retrieves HandRow records.
Duplicate hand_ids are silently ignored (idempotent inserts).
"""

import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.schema import ActionRow, HandRow, PlayerRow, StreetRow
from domain.hand import Hand

_STREET_ORDER = {"preflop": 0, "flop": 1, "turn": 2, "river": 3}


class HandRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_hand(self, hand: Hand) -> int | None:
        """Persist a Hand and all child rows.

        Returns the auto-generated DB id on success, or None if the hand_id
        already exists (duplicate silently skipped).
        """
        hand_row = HandRow(
            hand_id=hand.hand_id,
            game_type=hand.game_type.value,
            small_blind=hand.small_blind,
            big_blind=hand.big_blind,
            table_name=hand.table_name,
            played_at=hand.played_at.isoformat(),
            hero_name=hand.hero_name,
            pot=hand.pot,
            rake=hand.rake,
            cash_drop=hand.cash_drop,
            currency=hand.currency,
            is_walk=hand.is_walk,
            allin_equity_json=json.dumps(hand.all_in_equity) if hand.all_in_equity else None,
            allin_pot_bb=hand.all_in_pot_bb,
            allin_invested_bb=hand.all_in_invested_bb,
        )
        self._session.add(hand_row)

        try:
            self._session.flush()   # assigns hand_row.id, raises on duplicate
        except IntegrityError:
            self._session.rollback()
            return None

        for player in hand.players:
            self._session.add(PlayerRow(
                hand_id=hand_row.id,
                name=player.name,
                seat=player.seat,
                stack=player.stack,
                position=player.position.value if player.position else None,
                hole_cards=" ".join(player.hole_cards) if player.hole_cards else None,
                net_won=player.net_won,
                pot_won_after_rake=player.pot_won_after_rake,
            ))

        for street in hand.streets:
            order = _STREET_ORDER.get(street.name.value, 99)
            street_row = StreetRow(
                hand_id=hand_row.id,
                name=street.name.value,
                street_order=order,
                cards=" ".join(street.cards) if street.cards else None,
            )
            self._session.add(street_row)
            self._session.flush()   # assigns street_row.id

            for idx, action in enumerate(street.actions):
                self._session.add(ActionRow(
                    street_id=street_row.id,
                    action_order=idx,
                    player_name=action.player_name,
                    action_type=action.action_type.value,
                    amount=action.amount,
                    is_all_in=action.is_all_in,
                ))

        self._session.commit()
        return hand_row.id

    def get_hand(self, hand_id: str) -> HandRow | None:
        return self._session.query(HandRow).filter_by(hand_id=hand_id).one_or_none()
